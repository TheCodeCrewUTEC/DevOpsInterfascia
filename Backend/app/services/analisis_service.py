import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from app.database.connection import get_connection
from app.services import alerta_service, cache_service
from app.services.convocatoria_service import CONDICION_VISIBLE
from app.services.deteccion_alertas_service import ZONA_URUGUAY, hoy_uruguay, normalizar

# Análisis de datos (RF006). Los datos son pocos (cientos o miles de filas), así que
# SQL solo filtra por organismo y período; temáticas, estados, tops y relleno de
# huecos se calculan en Python con las funciones puras de arriba (testeables sin base).
# La temática no existe como columna: se deduce del texto igual que en RF005.

ESTADOS = ("Abierta", "Próxima", "Cerrada", "Otro", "Sin estado")
AGRUPACIONES = ("anio", "mes")

SIN_DATO = "Sin dato"
SIN_CLASIFICAR = "Sin clasificar"
OTROS = "Otros"
# Van siempre al final de las series, sin importar la cantidad
ETIQUETAS_AL_FINAL = (SIN_DATO, SIN_CLASIFICAR, "Sin estado", "Sin fecha", "Sin año")

LIMITE_TOP = 15
LIMITE_MESES = 120
LIMITE_ANIOS = 50
# Fuera de este rango es un dato mal cargado ("Proyecto 0007", fecha 0201-...): cuenta como sin año
ANIO_MINIMO = 1900
ANIO_MAXIMO = 2100
DIAS_CIERRE_PROXIMO = 30

SECTOR_NO_DISPONIBLE = {
    "disponible": False,
    "motivo": "Los datos de convocatorias no registran el sector económico.",
}
ORGANISMO_PROYECTOS_NO_DISPONIBLE = {
    "disponible": False,
    "motivo": "Los proyectos no registran organismo responsable.",
}

COLUMNAS_FONDOS = (
    "institucion", "estado", "fecha_apertura", "fecha_cierre",
    "titulo", "descripcion", "beneficiarios", "financiamiento",
)
COLUMNAS_INVESTIGADORES = (
    "institucion", "titulo", "investigaciones", "nivel_sni", "categoria_sni", "creado",
)
COLUMNAS_PROYECTOS = ("nombre", "estado", "anio", "descripcion")

FILTROS_FONDOS = ["organismo", "tematica", "estado", "periodo"]
FILTROS_INVESTIGADORES = ["organismo", "tematica"]
FILTROS_PROYECTOS = ["tematica", "periodo"]

# Espacios que se tratan como uno común. No se usa \s ni str.split(): en Postgres \s no
# incluye el espacio duro (U+00A0, el &nbsp; del HTML scrapeado) y en Python sí, y entonces
# el filtro no encontraba lo que mostraban las opciones. Esta misma clase de caracteres
# sirve tal cual como regex en Python y en Postgres (los dos entienden \t y \uXXXX).
# Incluye todo lo que str.split() toma como espacio, más U+200B y U+FEFF (invisibles).
CLASE_ESPACIOS = (
    r"[ \t\n\r\f\v\u001C-\u001F\u0085\u00A0\u1680\u2000-\u200B\u2028\u2029\u202F\u205F\u3000\uFEFF]+"
)
PATRON_ESPACIOS = re.compile(CLASE_ESPACIOS)

# Clave de organismo: espacios unificados y colapsados, sin bordes y en minúsculas. Tiene
# que dar lo mismo que clave_organismo() para que opciones, filtro, gráficos y resumen coincidan.
CLAVE_ORGANISMO_SQL = (
    f"lower(btrim(regexp_replace(COALESCE(institucion, ''), '{CLASE_ESPACIOS}', ' ', 'g')))"
)


@dataclass(frozen=True)
class FiltrosAnalisis:
    organismo: str | None = None
    tematica: str | None = None
    estado: str | None = None
    desde: date | None = None
    hasta: date | None = None

    def como_dict(self) -> dict:
        return {
            "organismo": self.organismo,
            "tematica": self.tematica,
            "estado": self.estado,
            "desde": self.desde.isoformat() if self.desde else None,
            "hasta": self.hasta.isoformat() if self.hasta else None,
        }

    @property
    def con_periodo(self) -> bool:
        return self.desde is not None or self.hasta is not None


# --- Funciones puras ---

def _texto(valor) -> str | None:
    if valor is None:
        return None
    texto = " ".join(str(valor).split())
    return texto or None


def _fecha(valor) -> date | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        # timestamptz (creado): el día que corresponde en Uruguay, no en UTC
        if valor.tzinfo is not None:
            valor = valor.astimezone(ZONA_URUGUAY)
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError:
        return None


def categoria_estado(texto) -> str:
    estado = normalizar(texto)

    if not estado:
        return "Sin estado"
    if "abiert" in estado:
        return "Abierta"
    if "proxim" in estado or "por abrir" in estado:
        return "Próxima"
    if "cerrad" in estado or "finaliz" in estado:
        return "Cerrada"
    return "Otro"


def tematicas_de(texto) -> list[str]:
    """Temáticas que aparecen como palabra completa: "Salud" no cuenta en "saludable"."""

    normalizado = normalizar(texto)
    if not normalizado:
        return []

    return [
        tematica for tematica in alerta_service.TEMATICAS
        if re.search(rf"(?<!\w){re.escape(normalizar(tematica))}(?!\w)", normalizado)
    ]


def institucion_principal(texto) -> str:
    """Primer tramo de la institución jerárquica: "Universidad de la República/ Facultad
    de Ingeniería / ... / Uruguay" queda en "Universidad de la República"."""

    for parte in str(texto or "").split("/"):
        parte = _texto(parte)
        if parte:
            return parte
    return SIN_DATO


def nivel_formacion(titulo) -> str:
    texto = normalizar(titulo)

    if not texto:
        return SIN_DATO
    if "doctor" in texto:
        return "Doctorado"
    if any(clave in texto for clave in ("magister", "maestr", "master")):
        return "Maestría"
    if "especializ" in texto:
        return "Especialización"
    if any(clave in texto for clave in ("licenci", "ingenier", "grado", "arquitect", "medic", "contador")):
        return "Grado"
    if "tecnic" in texto or "tecnolog" in texto:
        return "Técnico"
    return "Otro"


def anio_valido(anio: int | None) -> bool:
    return anio is not None and ANIO_MINIMO <= anio <= ANIO_MAXIMO


def anio_de(texto) -> int | None:
    """Primer año de 4 dígitos que aparezca suelto y esté entre 1900 y 2100
    ("2024", "2020-2023" → 2020); "s/d" o "Proyecto 0007" → None."""

    for encontrado in re.finditer(r"(?<!\w)(\d{4})(?!\w)", str(texto or "")):
        anio = int(encontrado.group(1))
        if anio_valido(anio):
            return anio
    return None


def _anio_fecha(valor) -> int | None:
    fecha = _fecha(valor)
    return fecha.year if fecha is not None and anio_valido(fecha.year) else None


def clave_organismo(texto) -> str:
    """Igual que CLAVE_ORGANISMO_SQL: "  ANII \t" y "anii" son el mismo organismo."""

    return colapsar_espacios(texto).lower()


def colapsar_espacios(texto) -> str:
    """Espacios de CLASE_ESPACIOS → uno común, sin bordes (como regexp_replace + btrim)."""

    return PATRON_ESPACIOS.sub(" ", str(texto or "")).strip(" ")


def etiquetas_organismo(conteo_variantes: dict) -> dict[str, str]:
    """Recibe {texto tal cual: cantidad} y devuelve {clave: etiqueta}. La etiqueta es la
    variante más escrita (con espacios colapsados); si empatan, la primera alfabética."""

    por_clave: dict[str, Counter] = {}
    for variante, cantidad in conteo_variantes.items():
        texto = colapsar_espacios(variante)
        if texto:
            por_clave.setdefault(clave_organismo(texto), Counter())[texto] += cantidad

    return {
        clave: min(variantes.items(), key=lambda par: (-par[1], par[0]))[0]
        for clave, variantes in por_clave.items()
    }


def por_organismo(instituciones: list) -> list[dict]:
    """Agrupa por clave_organismo mostrando la variante más frecuente; vacío → "Sin dato"."""

    etiquetas = etiquetas_organismo(Counter(instituciones))
    return top(contar(
        etiquetas[clave] if (clave := clave_organismo(texto)) else SIN_DATO
        for texto in instituciones
    ))


def contar(valores) -> list[dict]:
    """Serie ordenada por cantidad desc (empate: etiqueta asc); los "Sin ..." al final."""

    conteo = Counter(valores)
    principales = sorted(
        ((etiqueta, cantidad) for etiqueta, cantidad in conteo.items() if etiqueta not in ETIQUETAS_AL_FINAL),
        key=lambda par: (-par[1], par[0]),
    )
    al_final = [(etiqueta, conteo[etiqueta]) for etiqueta in ETIQUETAS_AL_FINAL if etiqueta in conteo]

    return [{"etiqueta": etiqueta, "cantidad": cantidad} for etiqueta, cantidad in principales + al_final]


def top(serie: list[dict], n: int = LIMITE_TOP) -> list[dict]:
    """Deja las n primeras, suma el resto en "Otros" y mantiene los "Sin ..." al final."""

    normales = [punto for punto in serie if punto["etiqueta"] not in ETIQUETAS_AL_FINAL]
    al_final = [punto for punto in serie if punto["etiqueta"] in ETIQUETAS_AL_FINAL]

    resultado = normales[:n]
    resto = sum(punto["cantidad"] for punto in normales[n:])
    if resto:
        resultado.append({"etiqueta": OTROS, "cantidad": resto})

    return resultado + al_final


def _serie_por_anio(anios: list[int | None], sin_valor: str) -> list[dict]:
    conteo = Counter(anio for anio in anios if anio is not None)
    serie = [{"etiqueta": f"{anio:04d}", "cantidad": conteo[anio]} for anio in sorted(conteo)]

    faltantes = sum(1 for anio in anios if anio is None)
    if faltantes:
        serie.append({"etiqueta": sin_valor, "cantidad": faltantes})

    return serie


def _periodo(fecha: date | None, agrupar: str) -> str | None:
    if fecha is None or not anio_valido(fecha.year):
        return None
    return f"{fecha.year:04d}" if agrupar == "anio" else f"{fecha.year:04d}-{fecha.month:02d}"


def periodos_entre(claves, agrupar: str) -> list[str]:
    """Todos los períodos de la primera a la última clave, sin huecos. Ignora las claves con
    año fuera de 1900–2100 y deja solo los últimos 50 años o los últimos 120 meses."""

    validas = [clave for clave in claves if anio_valido(int(clave[:4]))]
    if not validas:
        return []

    if agrupar == "anio":
        anios = [int(clave[:4]) for clave in validas]
        primero = max(min(anios), max(anios) - LIMITE_ANIOS + 1)
        return [f"{anio:04d}" for anio in range(primero, max(anios) + 1)]

    # Meses contados desde el año 0 para restar sin recorrer los huecos
    indices = [int(clave[:4]) * 12 + int(clave[5:7]) - 1 for clave in validas]
    primero = max(min(indices), max(indices) - LIMITE_MESES + 1)
    return [
        f"{indice // 12:04d}-{indice % 12 + 1:02d}"
        for indice in range(primero, max(indices) + 1)
    ]


def rellenar_periodos(conteo: dict[str, int], agrupar: str, periodos: list[str] | None = None) -> list[dict]:
    """Serie con 0 en los huecos. Si no se pasan los períodos salen de las claves del conteo;
    pasarlos sirve para que dos series compartan el mismo eje."""

    if periodos is None:
        periodos = periodos_entre(conteo, agrupar)

    return [{"periodo": periodo, "cantidad": conteo.get(periodo, 0)} for periodo in periodos]


def _escapar_like(valor: str) -> str:
    return valor.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def condiciones_fondos(filtros: FiltrosAnalisis) -> tuple[str, list]:
    """WHERE de convocatoria para organismo y período. Los valores van siempre como %s."""

    condiciones = [CONDICION_VISIBLE]
    parametros = []

    if filtros.organismo:
        condiciones.append(f"{CLAVE_ORGANISMO_SQL} = %s")
        parametros.append(clave_organismo(filtros.organismo))

    # Solapamiento: el fondo estuvo abierto algún día del período (falta una fecha → la otra)
    if filtros.desde is not None:
        condiciones.append("COALESCE(fecha_cierre, fecha_apertura) >= %s")
        parametros.append(filtros.desde)

    if filtros.hasta is not None:
        condiciones.append("COALESCE(fecha_apertura, fecha_cierre) <= %s")
        parametros.append(filtros.hasta)

    return " AND ".join(f"({condicion.strip()})" for condicion in condiciones), parametros


def _texto_fondo(fila: dict) -> str:
    return " ".join(fila.get(campo) or "" for campo in ("titulo", "descripcion", "beneficiarios"))


def _texto_proyecto(fila: dict) -> str:
    return " ".join(fila.get(campo) or "" for campo in ("nombre", "descripcion"))


def _texto_investigador(fila: dict) -> str:
    return " ".join(fila.get(campo) or "" for campo in ("titulo", "investigaciones"))


def _por_tematica(filas: list[dict], texto_de) -> list[dict]:
    valores = []
    for fila in filas:
        valores.extend(tematicas_de(texto_de(fila)) or [SIN_CLASIFICAR])
    return contar(valores)


def _estado_proyecto(texto) -> str:
    estado = normalizar(texto)
    if not estado:
        return SIN_DATO
    if "curso" in estado:
        return "En curso"
    if "finaliz" in estado:
        return "Finalizado"
    return _texto(texto)


def _lineas(investigaciones) -> int:
    return sum(1 for linea in str(investigaciones or "").split("\n") if linea.strip())


# --- Lectura de la base ---

def _existe_tabla(cur, nombre: str) -> bool:
    # convocatoria la crea el scraping, no ensure_schema: en una base nueva puede no estar
    cur.execute("SELECT to_regclass(%s)", (f"public.{nombre}",))
    fila = cur.fetchone()
    return fila is not None and fila[0] is not None


def _como_dicts(filas, columnas) -> list[dict]:
    return [dict(zip(columnas, fila)) for fila in filas]


def _leer_fondos(cur, filtros: FiltrosAnalisis) -> list[dict] | None:
    """None si la tabla no existe. Organismo y período en SQL; temática y estado acá."""

    if not _existe_tabla(cur, "convocatoria"):
        return None

    where, parametros = condiciones_fondos(filtros)
    cur.execute(
        f"""
        SELECT {", ".join(COLUMNAS_FONDOS)}
        FROM convocatoria
        WHERE {where}
        """,
        parametros
    )
    filas = _como_dicts(cur.fetchall(), COLUMNAS_FONDOS)

    if filtros.tematica:
        filas = [f for f in filas if filtros.tematica in tematicas_de(_texto_fondo(f))]
    if filtros.estado:
        filas = [f for f in filas if categoria_estado(f["estado"]) == filtros.estado]

    return filas


def _leer_investigadores(cur, filtros: FiltrosAnalisis) -> list[dict] | None:
    """El período no aplica: no hay fechas de la actividad, solo de carga."""

    if not _existe_tabla(cur, "investigadores"):
        return None

    where = ""
    parametros = []
    if filtros.organismo:
        # Parcial: la institución es jerárquica ("Universidad de la República/ Facultad...")
        where = f"WHERE regexp_replace(institucion, '{CLASE_ESPACIOS}', ' ', 'g') ILIKE %s"
        parametros.append(f"%{_escapar_like(colapsar_espacios(filtros.organismo))}%")

    cur.execute(
        f"""
        SELECT {", ".join(COLUMNAS_INVESTIGADORES)}
        FROM investigadores
        {where}
        """,
        parametros
    )
    filas = _como_dicts(cur.fetchall(), COLUMNAS_INVESTIGADORES)

    if filtros.tematica:
        filas = [f for f in filas if filtros.tematica in tematicas_de(_texto_investigador(f))]

    return filas


def _leer_proyectos(cur, filtros: FiltrosAnalisis) -> list[dict] | None:
    """El año es texto libre: el período se aplica acá con anio_de. Con período activo
    quedan afuera los proyectos sin año legible. Organismo y estado no aplican."""

    if not _existe_tabla(cur, "proyectos"):
        return None

    cur.execute(f"SELECT {', '.join(COLUMNAS_PROYECTOS)} FROM proyectos")
    filas = _como_dicts(cur.fetchall(), COLUMNAS_PROYECTOS)

    if filtros.con_periodo:
        def en_periodo(fila):
            anio = anio_de(fila["anio"])
            if anio is None:
                return False
            if filtros.desde is not None and anio < filtros.desde.year:
                return False
            if filtros.hasta is not None and anio > filtros.hasta.year:
                return False
            return True

        filas = [f for f in filas if en_periodo(f)]

    if filtros.tematica:
        filas = [f for f in filas if filtros.tematica in tematicas_de(_texto_proyecto(f))]

    return filas


def _leer(*lectores, filtros: FiltrosAnalisis) -> list:
    """Corre los lectores con una sola conexión."""

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            return [lector(cur, filtros) for lector in lectores]
    finally:
        conn.close()


def _con_cache(seccion: str, parametros: dict, calcular):
    clave_cache = cache_service.clave(f"analisis:{seccion}", parametros)
    guardado = cache_service.leer(clave_cache)
    if guardado is not None:
        return guardado

    resultado = calcular()
    cache_service.guardar(clave_cache, resultado)
    return resultado


# --- Armado de cada sección (puro, a partir de las filas) ---

def armar_fondos(filas: list[dict] | None) -> dict:
    filas = filas or []

    anios_apertura = [_anio_fecha(f["fecha_apertura"]) for f in filas]
    informado = sum(1 for f in filas if _texto(f["financiamiento"]))

    return {
        "disponible": True,
        "filtros_aplicados": FILTROS_FONDOS,
        "total": len(filas),
        "por_organismo": por_organismo([f["institucion"] for f in filas]),
        "por_tematica": _por_tematica(filas, _texto_fondo),
        "por_estado": contar(categoria_estado(f["estado"]) for f in filas),
        "por_anio_apertura": _serie_por_anio(anios_apertura, "Sin fecha"),
        "por_sector_economico": dict(SECTOR_NO_DISPONIBLE),
        "financiamiento": {"informado": informado, "sin_informar": len(filas) - informado},
        "tematica_multiple": True,
    }


def armar_investigadores(filas: list[dict] | None) -> dict:
    filas = filas or []
    lineas = sum(_lineas(f["investigaciones"]) for f in filas)

    return {
        "disponible": True,
        "filtros_aplicados": FILTROS_INVESTIGADORES,
        "total": len(filas),
        "por_institucion": top(contar(institucion_principal(f["institucion"]) for f in filas)),
        "por_nivel_sni": contar(_texto(f["nivel_sni"]) or SIN_DATO for f in filas),
        "por_categoria_sni": contar(_texto(f["categoria_sni"]) or SIN_DATO for f in filas),
        "por_formacion": contar(nivel_formacion(f["titulo"]) for f in filas),
        "por_area_tematica": _por_tematica(filas, _texto_investigador),
        "lineas_investigacion": {
            "total": lineas,
            "promedio_por_investigador": round(lineas / len(filas), 1) if filas else 0.0,
        },
    }


def armar_proyectos(filas: list[dict] | None) -> dict:
    filas = filas or []

    return {
        "disponible": True,
        "filtros_aplicados": FILTROS_PROYECTOS,
        "total": len(filas),
        "por_estado": contar(_estado_proyecto(f["estado"]) for f in filas),
        "por_anio": _serie_por_anio([anio_de(f["anio"]) for f in filas], "Sin año"),
        "por_tematica": _por_tematica(filas, _texto_proyecto),
        "por_organismo": dict(ORGANISMO_PROYECTOS_NO_DISPONIBLE),
    }


def _no_disponible(seccion: dict) -> dict:
    """Misma forma que la sección, con total 0 y series vacías."""

    vacia = {}
    for campo, valor in seccion.items():
        if campo == "total":
            vacia[campo] = 0
        elif isinstance(valor, list) and campo != "filtros_aplicados":
            vacia[campo] = []
        else:
            vacia[campo] = valor
    vacia["disponible"] = False
    return vacia


def _seccion(filas, armar) -> dict:
    seccion = armar(filas)
    return seccion if filas is not None else _no_disponible(seccion)


# --- API del service ---

def _leer_organismos(cur) -> list[str]:
    """Organismos de las convocatorias visibles, uno por clave_organismo. No se usa
    alerta_service.instituciones_disponibles() porque esa incluye las no visibles."""

    if not _existe_tabla(cur, "convocatoria"):
        return []

    cur.execute(
        f"""
        SELECT institucion, COUNT(*)
        FROM convocatoria
        WHERE {CONDICION_VISIBLE}
          AND btrim(COALESCE(institucion, '')) <> ''
        GROUP BY institucion
        """
    )
    etiquetas = etiquetas_organismo(dict(cur.fetchall()))
    return sorted(etiquetas.values(), key=lambda etiqueta: (normalizar(etiqueta), etiqueta))


def obtener_opciones() -> dict:
    def calcular():
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                organismos = _leer_organismos(cur)
        finally:
            conn.close()

        return {
            "organismos": organismos,
            "tematicas": list(alerta_service.TEMATICAS),
            "estados": list(ESTADOS),
            "sector_economico": dict(SECTOR_NO_DISPONIBLE),
        }

    return _con_cache("opciones", {}, calcular)


def obtener_resumen(filtros: FiltrosAnalisis) -> dict:
    def calcular():
        fondos, investigadores, proyectos = _leer(
            _leer_fondos, _leer_investigadores, _leer_proyectos, filtros=filtros
        )
        hoy = hoy_uruguay()
        limite = hoy + timedelta(days=DIAS_CIERRE_PROXIMO)

        lista_fondos = fondos or []
        estados = Counter(categoria_estado(f["estado"]) for f in lista_fondos)
        lista_inv = investigadores or []
        lista_proy = proyectos or []
        estados_proy = Counter(_estado_proyecto(p["estado"]) for p in lista_proy)

        return {
            "filtros": filtros.como_dict(),
            "fondos": {
                "disponible": fondos is not None,
                "filtros_aplicados": FILTROS_FONDOS,
                "total": len(lista_fondos),
                "abiertos": estados["Abierta"],
                "proximos": estados["Próxima"],
                "cerrados": estados["Cerrada"],
                "cierran_30_dias": sum(
                    1 for f in lista_fondos
                    if categoria_estado(f["estado"]) == "Abierta"
                    and (cierre := _fecha(f["fecha_cierre"])) is not None
                    and hoy <= cierre <= limite
                ),
                "organismos": len({
                    clave for f in lista_fondos if (clave := clave_organismo(f["institucion"]))
                }),
                "con_financiamiento": sum(1 for f in lista_fondos if _texto(f["financiamiento"])),
            },
            "investigadores": {
                "disponible": investigadores is not None,
                "filtros_aplicados": FILTROS_INVESTIGADORES,
                "total": len(lista_inv),
                "instituciones": len({
                    principal for i in lista_inv
                    if (principal := institucion_principal(i["institucion"])) != SIN_DATO
                }),
                "con_nivel_sni": sum(1 for i in lista_inv if _texto(i["nivel_sni"])),
            },
            "proyectos": {
                "disponible": proyectos is not None,
                "filtros_aplicados": FILTROS_PROYECTOS,
                "total": len(lista_proy),
                "en_curso": estados_proy["En curso"],
                "finalizados": estados_proy["Finalizado"],
            },
            "generado": datetime.now(timezone.utc).isoformat(),
        }

    return _con_cache("resumen", filtros.como_dict(), calcular)


def obtener_fondos(filtros: FiltrosAnalisis) -> dict:
    def calcular():
        (fondos,) = _leer(_leer_fondos, filtros=filtros)
        return _seccion(fondos, armar_fondos)

    return _con_cache("fondos", filtros.como_dict(), calcular)


def obtener_investigadores(filtros: FiltrosAnalisis) -> dict:
    def calcular():
        (investigadores,) = _leer(_leer_investigadores, filtros=filtros)
        return _seccion(investigadores, armar_investigadores)

    return _con_cache("investigadores", filtros.como_dict(), calcular)


def obtener_proyectos(filtros: FiltrosAnalisis) -> dict:
    def calcular():
        (proyectos,) = _leer(_leer_proyectos, filtros=filtros)
        return _seccion(proyectos, armar_proyectos)

    return _con_cache("proyectos", filtros.como_dict(), calcular)


def armar_tendencias(fondos, proyectos, investigadores, agrupar: str) -> dict:
    def conteo(fechas, agrupacion):
        return Counter(p for fecha in fechas if (p := _periodo(_fecha(fecha), agrupacion)))

    lista_fondos = fondos or []
    anios_proyectos = Counter(
        f"{anio:04d}" for p in (proyectos or []) if (anio := anio_de(p["anio"])) is not None
    )

    # Apertura y cierre comparten eje: la unión de los dos rangos, con un solo tope
    aperturas = conteo((f["fecha_apertura"] for f in lista_fondos), agrupar)
    cierres = conteo((f["fecha_cierre"] for f in lista_fondos), agrupar)
    periodos_fondos = periodos_entre(set(aperturas) | set(cierres), agrupar)

    return {
        "agrupar": agrupar,
        "filtros_aplicados": {
            "fondos": FILTROS_FONDOS,
            "proyectos": FILTROS_PROYECTOS,
            "investigadores": FILTROS_INVESTIGADORES,
        },
        "fondos_por_apertura": rellenar_periodos(aperturas, agrupar, periodos_fondos),
        "fondos_por_cierre": rellenar_periodos(cierres, agrupar, periodos_fondos),
        # El año de los proyectos es texto libre: no hay mes
        "proyectos_por_anio": rellenar_periodos(anios_proyectos, "anio"),
        "investigadores_incorporados": rellenar_periodos(
            conteo((i["creado"] for i in (investigadores or [])), agrupar), agrupar
        ),
        "disponible": {
            "fondos": fondos is not None,
            "proyectos": proyectos is not None,
            "investigadores": investigadores is not None,
        },
    }


def obtener_tendencias(filtros: FiltrosAnalisis, agrupar: str = "anio") -> dict:
    def calcular():
        fondos, proyectos, investigadores = _leer(
            _leer_fondos, _leer_proyectos, _leer_investigadores, filtros=filtros
        )
        return armar_tendencias(fondos, proyectos, investigadores, agrupar)

    return _con_cache("tendencias", {**filtros.como_dict(), "agrupar": agrupar}, calcular)
