import re
from datetime import date

from app.database.connection import get_connection
from app.services import cache_service
from app.services.documento_service import obtener_documento_por_convocatoria

# El texto de la convocatoria no tiene columnas aparte para estos criterios.
TEXTO = "concat_ws(' ', titulo, descripcion, beneficiarios, requisitos)"
NACIONAL = (
    r"todo el pa[ií]s|todo uruguay|[áa]mbito nacional|nivel nacional|"
    r"territorio nacional|regi[oó]n nacional"
)
VOCALES = {
    "a": "[aá]",
    "e": "[eé]",
    "i": "[ií]",
    "o": "[oó]",
    "u": "[uúü]",
}

DEPARTAMENTOS = [
    "Artigas",
    "Canelones",
    "Cerro Largo",
    "Colonia",
    "Durazno",
    "Flores",
    "Florida",
    "Lavalleja",
    "Maldonado",
    "Montevideo",
    "Paysandú",
    "Río Negro",
    "Rivera",
    "Rocha",
    "Salto",
    "San José",
    "Soriano",
    "Tacuarembó",
    "Treinta y Tres",
]

BENEFICIARIOS = {
    "mipymes": ("mipyme|micro,?\\s+peque|pequeñas y medianas|micro y peque", "Mipymes"),
    "grandes": ("grandes empresas|gran empresa", "Grandes empresas"),
    "instituciones": (
        "instituci[oó]n|c[áa]mara|asociaci[oó]n|gremial",
        "Instituciones y cámaras",
    ),
    "personas": ("persona f[ií]sica|personas f[ií]sicas|emprendedor", "Personas y emprendedores"),
    "cooperativas": ("cooperativa", "Cooperativas"),
    "turismo": ("tur[ií]stic|turismo", "Sector turístico"),
    "productores": ("productor", "Productores"),
}

TEMATICAS = {
    "innovacion": ("innovaci[oó]n", "Innovación"),
    "tecnologia": ("tecnolog|digital|transformaci[oó]n digital", "Tecnología y digital"),
    "agro": ("agro|pesca|bioeconom", "Agro y pesca"),
    "economia_circular": ("circular|bioeconom", "Economía circular"),
    "turismo": ("turism|tur[ií]stic", "Turismo"),
    "audiovisual": ("audiovisual", "Audiovisual"),
    "territorial": ("territorial|desarrollo local", "Desarrollo territorial"),
    "energia": ("energ[ií]a", "Energía"),
    "salud": ("salud", "Salud"),
    "educacion": ("educaci[oó]n|formaci[oó]n", "Educación y formación"),
    "medio_ambiente": ("ambiente|sostenib|sustentab", "Medio ambiente"),
}

REGIONES = {
    "este": ("regi[oó]n este", "Este"),
    "sur": ("regi[oó]n sur", "Sur"),
    "litoral": ("regi[oó]n litoral", "Litoral"),
    "noreste": ("regi[oó]n noreste", "Noreste"),
    "norte": ("regi[oó]n norte", "Norte"),
    "centro": ("regi[oó]n centro", "Centro"),
}


def _opciones(catalogo: dict[str, tuple[str, str]]):
    return [{"id": clave, "label": etiqueta} for clave, (_, etiqueta) in catalogo.items()]


def _patron_lugar(texto: str) -> str:
    limpio = " ".join(texto.strip().split())
    if len(limpio) < 2 or len(limpio) > 80:
        raise ValueError("Escribí una localidad válida.")
    if not re.fullmatch(r"[A-Za-zÁÉÍÓÚÜáéíóúüÑñ \-']+", limpio):
        raise ValueError("Escribí una localidad válida.")

    partes = []
    for caracter in limpio.lower():
        base = (
            caracter.replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
            .replace("ü", "u")
        )
        if base in VOCALES:
            partes.append(VOCALES[base])
        elif caracter == "ñ":
            partes.append("[nñ]")
        elif caracter == " ":
            partes.append(r"\s+")
        elif caracter in "-'":
            partes.append(re.escape(caracter))
        else:
            partes.append(re.escape(base))
    return "".join(partes)


def _filtro_ubicacion(alcance: str | None, ubicacion: str | None):
    if alcance is None:
        return None
    if alcance == "todo_uruguay":
        return NACIONAL
    if not ubicacion or not ubicacion.strip():
        raise ValueError("Elegí una ubicación.")
    if alcance == "departamento":
        if ubicacion not in DEPARTAMENTOS:
            raise ValueError("Elegí un departamento válido.")
        return _patron_lugar(ubicacion)
    if alcance == "region":
        region = REGIONES.get(ubicacion)
        if region is None:
            raise ValueError("Elegí una región válida.")
        return region[0]
    if alcance == "localidad":
        return _patron_lugar(ubicacion)
    raise ValueError("El alcance de ubicación no es válido.")


def opciones_convocatorias():
    conn = get_connection()
    cursor = conn.cursor()
    visibles = """
        btrim(COALESCE(descripcion, '')) <> ''
        AND (fecha_apertura IS NOT NULL OR fecha_cierre IS NOT NULL)
    """
    try:
        cursor.execute(
            f"""
            SELECT DISTINCT btrim(estado)
            FROM convocatoria
            WHERE {visibles}
              AND estado IS NOT NULL
              AND btrim(estado) <> ''
            ORDER BY 1
            """
        )
        estados = [fila[0] for fila in cursor.fetchall()]
        cursor.execute(
            f"""
            SELECT DISTINCT btrim(institucion)
            FROM convocatoria
            WHERE {visibles}
              AND institucion IS NOT NULL
              AND btrim(institucion) <> ''
            ORDER BY 1
            """
        )
        instituciones = [fila[0] for fila in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()

    return {
        "estados": estados,
        "instituciones": instituciones,
        "beneficiarios": _opciones(BENEFICIARIOS),
        "tematicas": _opciones(TEMATICAS),
        "departamentos": DEPARTAMENTOS,
        "regiones": _opciones(REGIONES),
    }


# Temporal: el repositorio y Relacionar muestran solo convocatorias
# que ya tienen descripción y al menos una fecha. La analítica (RF006)
# usa la misma condición para contar lo mismo que se ve en el repositorio.
CONDICION_VISIBLE = """
    btrim(COALESCE(descripcion, '')) <> ''
    AND (
        fecha_apertura IS NOT NULL
        OR fecha_cierre IS NOT NULL
    )
"""

def obtener_convocatorias(
    estado: str | None = None,
    institucion: str | None = None,
    buscar: str | None = None,
    fecha_apertura_desde: date | None = None,
    fecha_apertura_hasta: date | None = None,
    fecha_cierre_desde: date | None = None,
    fecha_cierre_hasta: date | None = None,
    beneficiario: str | None = None,
    tematica: str | None = None,
    alcance: str | None = None,
    ubicacion: str | None = None,
    financiamiento_min: int | None = None,
    financiamiento_max: int | None = None,
    proximas_a_abrir: bool = False,
    page: int = 1,
    limit: int = 20
):

    # El listado se repite mucho (repositorio, Relacionar): se guarda unos minutos en Redis
    clave_cache = cache_service.clave("convocatorias", locals())
    guardado = cache_service.leer(clave_cache)
    if guardado is not None:
        return guardado

    resultado = _consultar_convocatorias(
        estado, institucion, buscar,
        fecha_apertura_desde, fecha_apertura_hasta,
        fecha_cierre_desde, fecha_cierre_hasta,
        beneficiario, tematica, alcance, ubicacion,
        financiamiento_min, financiamiento_max,
        proximas_a_abrir,
        page, limit,
    )
    cache_service.guardar(clave_cache, resultado)
    return resultado


def _consultar_convocatorias(
    estado, institucion, buscar,
    fecha_apertura_desde, fecha_apertura_hasta,
    fecha_cierre_desde, fecha_cierre_hasta,
    beneficiario, tematica, alcance, ubicacion,
    financiamiento_min, financiamiento_max,
    proximas_a_abrir,
    page, limit,
):

    conn = get_connection()
    cursor = conn.cursor()

    try:
        return _listar_convocatorias(
            cursor,
            estado=estado,
            institucion=institucion,
            buscar=buscar,
            fecha_apertura_desde=fecha_apertura_desde,
            fecha_apertura_hasta=fecha_apertura_hasta,
            fecha_cierre_desde=fecha_cierre_desde,
            fecha_cierre_hasta=fecha_cierre_hasta,
            beneficiario=beneficiario,
            tematica=tematica,
            alcance=alcance,
            ubicacion=ubicacion,
            financiamiento_min=financiamiento_min,
            financiamiento_max=financiamiento_max,
            proximas_a_abrir=proximas_a_abrir,
            page=page,
            limit=limit,
        )
    finally:
        cursor.close()
        conn.close()


def _listar_convocatorias(
    cursor,
    estado,
    institucion,
    buscar,
    fecha_apertura_desde,
    fecha_apertura_hasta,
    fecha_cierre_desde,
    fecha_cierre_hasta,
    beneficiario,
    tematica,
    alcance,
    ubicacion,
    financiamiento_min,
    financiamiento_max,
    proximas_a_abrir,
    page,
    limit,
):
    where = ""
    parametros = []

    # Temporal (ver CONDICION_VISIBLE). Quitar esta línea para volver a listar todas.
    where += f" AND {CONDICION_VISIBLE}"

    if estado is not None:
        where += " AND LOWER(estado) LIKE LOWER(%s)"
        parametros.append(f"%{estado}%")

    if institucion is not None:
        where += " AND LOWER(institucion) LIKE LOWER(%s)"
        parametros.append(f"%{institucion}%")

    if buscar is not None and buscar.strip() != "":
        where += """
            AND (
                titulo ILIKE %s
                OR COALESCE(descripcion, '') ILIKE %s
                OR COALESCE(institucion, '') ILIKE %s
                OR COALESCE(beneficiarios, '') ILIKE %s
            )
        """
        patron = f"%{buscar.strip()}%"
        parametros.extend([patron] * 4)

    if fecha_apertura_desde is not None:
        where += " AND fecha_apertura >= %s"
        parametros.append(fecha_apertura_desde)

    if fecha_apertura_hasta is not None:
        where += " AND fecha_apertura <= %s"
        parametros.append(fecha_apertura_hasta)

    if fecha_cierre_desde is not None:
        where += " AND fecha_cierre >= %s"
        parametros.append(fecha_cierre_desde)

    if fecha_cierre_hasta is not None:
        where += " AND fecha_cierre <= %s"
        parametros.append(fecha_cierre_hasta)

    if beneficiario is not None:
        opcion = BENEFICIARIOS.get(beneficiario)
        if opcion is None:
            raise ValueError("Elegí un tipo de beneficiario válido.")
        where += f" AND {TEXTO} ~* %s"
        parametros.append(opcion[0])

    if tematica is not None:
        opcion = TEMATICAS.get(tematica)
        if opcion is None:
            raise ValueError("Elegí un área temática válida.")
        where += f" AND {TEXTO} ~* %s"
        parametros.append(opcion[0])

    patron_ubicacion = _filtro_ubicacion(alcance, ubicacion)
    if patron_ubicacion is not None:
        where += f" AND {TEXTO} ~* %s"
        parametros.append(patron_ubicacion)

    if financiamiento_min is not None or financiamiento_max is not None:
        where += " AND financiamiento ~ '^[0-9]+$'"
        if (
            financiamiento_min is not None
            and financiamiento_max is not None
            and financiamiento_min > financiamiento_max
        ):
            raise ValueError("El monto mínimo no puede ser mayor que el máximo.")
        if financiamiento_min is not None:
            where += " AND financiamiento::bigint >= %s"
            parametros.append(financiamiento_min)
        if financiamiento_max is not None:
            where += " AND financiamiento::bigint <= %s"
            parametros.append(financiamiento_max)

    if proximas_a_abrir:
        where += " AND fecha_apertura >= CURRENT_DATE"

    cursor.execute(
        f"""
        SELECT COUNT(*)
        FROM convocatoria
        WHERE 1=1
        {where}
        """,
        parametros
    )

    total = cursor.fetchone()[0]

    offset = (page - 1) * limit

    cursor.execute(
        f"""
        SELECT
            id,
            titulo,
            institucion,
            estado,
            fecha_apertura,
            fecha_cierre,
            descripcion,
            beneficiarios,
            requisitos,
            financiamiento,
            creado
        FROM convocatoria
        WHERE 1=1
        {where}
        ORDER BY
            CASE WHEN lower(btrim(estado)) = 'abierta' THEN 0 ELSE 1 END,
            GREATEST(fecha_apertura, fecha_cierre) DESC NULLS LAST,
            id DESC
        LIMIT %s
        OFFSET %s
        """,
        parametros + [limit, offset]
    )
    
    rows = cursor.fetchall()

    convocatorias = []

    for row in rows:
        convocatorias.append({
            "id": row[0],
            "titulo": row[1],
            "institucion": row[2],
            "estado": row[3],
            "fecha_apertura": row[4],
            "fecha_cierre": row[5],
            "descripcion": row[6],
            "beneficiarios": row[7],
            "requisitos": row[8],
            "financiamiento": row[9],
            "creado": row[10]
        })

    total_pages = (total + limit - 1) // limit

    return {
        "items": convocatorias,
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages
    }

def obtener_convocatoria(id: int):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            titulo,
            institucion,
            estado,
            fecha_apertura,
            fecha_cierre,
            descripcion,
            beneficiarios,
            requisitos,
            financiamiento,
            fuente,
            creado
        FROM convocatoria
        WHERE id = %s
    """, (id,))

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if row is None:
        return None

    # Obtener documentos relacionados
    documentos = obtener_documento_por_convocatoria(id)

    return {
        "id": row[0],
        "titulo": row[1],
        "institucion": row[2],
        "estado": row[3],
        "fecha_apertura": row[4],
        "fecha_cierre": row[5],
        "descripcion": row[6],
        "beneficiarios": row[7],
        "requisitos": row[8],
        "financiamiento": row[9],
        "fuente": row[10],
        "creado": row[11],
        "documentos": documentos
    }