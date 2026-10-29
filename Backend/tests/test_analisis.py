from datetime import date, datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import obtener_usuario_actual
from app.routers import analisis
from app.services import analisis_service
from app.services.analisis_service import (
    FiltrosAnalisis,
    anio_de,
    categoria_estado,
    clave_organismo,
    condiciones_fondos,
    contar,
    etiquetas_organismo,
    institucion_principal,
    nivel_formacion,
    por_organismo,
    rellenar_periodos,
    tematicas_de,
    top,
)
from app.services.convocatoria_service import CONDICION_VISIBLE

USUARIO = {"sub": "usuario-1", "email": "ana@example.com"}

app = FastAPI()
app.include_router(analisis.router)
app.dependency_overrides[obtener_usuario_actual] = lambda: USUARIO

client = TestClient(app)

# Sin override: obtener_usuario_actual de verdad, que exige token
app_sin_token = FastAPI()
app_sin_token.include_router(analisis.router)
client_sin_token = TestClient(app_sin_token)

RUTAS = [
    "/api/analisis/opciones",
    "/api/analisis/resumen",
    "/api/analisis/fondos",
    "/api/analisis/investigadores",
    "/api/analisis/proyectos",
    "/api/analisis/tendencias",
]


# --- Funciones puras ---

def test_tematicas_ignora_tildes_y_mayusculas():
    assert tematicas_de("Fondo de INNOVACION en educacion") == ["Innovación", "Educación"]
    assert tematicas_de("medio   AMBIENTE y energía") == ["Energía", "Medio ambiente"]


def test_tematicas_palabra_completa():
    assert tematicas_de("Fondo para la salud rural") == ["Salud"]
    assert tematicas_de("Alimentación saludable") == []
    assert tematicas_de("") == []


def test_ute_no_coincide_con_utec(monkeypatch):
    monkeypatch.setattr(analisis_service.alerta_service, "TEMATICAS", ("UTE",))
    assert tematicas_de("Convenio con UTEC") == []
    assert tematicas_de("Convenio con UTE.") == ["UTE"]

    filtros = FiltrosAnalisis(organismo="UTE")
    # El organismo de fondos se compara exacto en SQL, nunca con LIKE
    sql, parametros = condiciones_fondos(filtros)
    assert "LIKE" not in sql.upper()
    assert parametros == ["ute"]


def test_categoria_estado():
    assert categoria_estado("Abierta") == "Abierta"
    assert categoria_estado("  ABIERTO hasta marzo") == "Abierta"
    assert categoria_estado("Próxima") == "Próxima"
    assert categoria_estado("proximamente") == "Próxima"
    assert categoria_estado("Por abrir") == "Próxima"
    assert categoria_estado("Cerrada") == "Cerrada"
    assert categoria_estado("Finalizada") == "Cerrada"
    assert categoria_estado("") == "Sin estado"
    assert categoria_estado(None) == "Sin estado"
    assert categoria_estado("Suspendida") == "Otro"


def test_nivel_formacion():
    assert nivel_formacion("Doctor en Física") == "Doctorado"
    assert nivel_formacion("Magíster en Ingeniería") == "Maestría"
    assert nivel_formacion("Maestría en Biología") == "Maestría"
    assert nivel_formacion("Master of Science") == "Maestría"
    assert nivel_formacion("Especialización en Gestión") == "Especialización"
    assert nivel_formacion("Ingeniero Agrónomo") == "Grado"
    assert nivel_formacion("Licenciada en Química") == "Grado"
    assert nivel_formacion("Técnico en Informática") == "Técnico"
    assert nivel_formacion("Tecnólogo Químico") == "Técnico"
    assert nivel_formacion("Bachiller") == "Otro"
    assert nivel_formacion("") == "Sin dato"
    assert nivel_formacion(None) == "Sin dato"


def test_institucion_principal():
    texto = "Universidad de la República/ Facultad de Ingeniería / Instituto de Física / Uruguay"
    assert institucion_principal(texto) == "Universidad de la República"
    assert institucion_principal("  /  Instituto Pasteur ") == "Instituto Pasteur"
    assert institucion_principal("") == "Sin dato"
    assert institucion_principal(None) == "Sin dato"


def test_anio_de():
    assert anio_de("2024") == 2024
    assert anio_de(" 2020 - 2023") == 2020
    assert anio_de("s/d") is None
    assert anio_de("12345") is None
    assert anio_de(None) is None


def test_contar_ordena_y_deja_sin_dato_al_final():
    serie = contar(["B", "A", "Sin dato", "B", "Sin dato", "Sin dato", "C"])
    assert serie == [
        {"etiqueta": "B", "cantidad": 2},
        {"etiqueta": "A", "cantidad": 1},
        {"etiqueta": "C", "cantidad": 1},
        {"etiqueta": "Sin dato", "cantidad": 3},
    ]


def test_top_agrupa_en_otros():
    valores = [f"Org {i:02d}" for i in range(20) for _ in range(20 - i)] + ["Sin dato"]
    serie = top(contar(valores), n=15)

    assert len(serie) == 17
    assert [p["etiqueta"] for p in serie[-2:]] == ["Otros", "Sin dato"]
    # Org 15..19 tienen 5, 4, 3, 2 y 1
    assert serie[-2]["cantidad"] == 15
    assert sum(p["cantidad"] for p in serie) == len(valores)


def test_top_sin_resto_no_agrega_otros():
    serie = top(contar(["A", "B"]))
    assert [p["etiqueta"] for p in serie] == ["A", "B"]


def test_rellenar_periodos_por_anio():
    assert rellenar_periodos({"2021": 2, "2024": 1}, "anio") == [
        {"periodo": "2021", "cantidad": 2},
        {"periodo": "2022", "cantidad": 0},
        {"periodo": "2023", "cantidad": 0},
        {"periodo": "2024", "cantidad": 1},
    ]
    assert rellenar_periodos({}, "anio") == []


def test_rellenar_periodos_por_mes_cruza_el_anio():
    assert rellenar_periodos({"2024-11": 1, "2025-02": 3}, "mes") == [
        {"periodo": "2024-11", "cantidad": 1},
        {"periodo": "2024-12", "cantidad": 0},
        {"periodo": "2025-01", "cantidad": 0},
        {"periodo": "2025-02", "cantidad": 3},
    ]


def test_rellenar_periodos_por_mes_limita_a_120():
    serie = rellenar_periodos({"2000-01": 1, "2025-12": 2}, "mes")
    assert len(serie) == 120
    assert serie[0]["periodo"] == "2016-01"
    assert serie[-1] == {"periodo": "2025-12", "cantidad": 2}


def test_condiciones_fondos_parametriza():
    organismo = "O'Higgins'; DROP TABLE convocatoria; --"
    filtros = FiltrosAnalisis(
        organismo=organismo,
        desde=date(2024, 1, 1),
        hasta=date(2024, 12, 31),
    )

    sql, parametros = condiciones_fondos(filtros)

    assert organismo not in sql
    assert "higgins" not in sql.lower()
    assert "2024" not in sql
    assert sql.count("%s") == 3
    assert parametros == [organismo.lower(), date(2024, 1, 1), date(2024, 12, 31)]
    assert CONDICION_VISIBLE.strip() in sql


def test_condiciones_fondos_organismo_con_espacios_y_mayusculas():
    sql, parametros = condiciones_fondos(FiltrosAnalisis(organismo="  Agencia \t  NACIONAL "))
    # La base compara contra la misma clave: espacios colapsados, sin bordes, minúsculas
    assert analisis_service.CLAVE_ORGANISMO_SQL in sql
    assert "regexp_replace" in sql and analisis_service.CLASE_ESPACIOS in sql
    assert parametros == ["agencia nacional"]


def test_clave_organismo():
    assert clave_organismo("  ANII \t ") == "anii"
    assert clave_organismo("Agencia  Nacional\tde\nInvestigación") == "agencia nacional de investigación"
    assert clave_organismo(None) == ""


@pytest.mark.parametrize("espacio", ["\u00a0", "\u2007", "\u202f", "\u200b", "\t", "\n", "\u3000", "\ufeff"])
def test_clave_organismo_espacios_unicode(espacio):
    assert clave_organismo(f"MEC{espacio}") == "mec"
    assert clave_organismo(f"{espacio}Agencia{espacio}{espacio}Nacional") == "agencia nacional"


def test_clase_espacios_cubre_lo_que_split_considera_espacio():
    import sys

    espacios = [chr(c) for c in range(sys.maxunicode + 1) if chr(c).isspace()]
    assert all(analisis_service.PATRON_ESPACIOS.fullmatch(e) for e in espacios)


def test_espacio_duro_mismo_organismo_en_opciones_grafico_y_filtro():
    etiquetas = etiquetas_organismo({"MEC\u00a0": 1, "MEC": 1})
    assert etiquetas == {"mec": "MEC"}
    assert por_organismo(["MEC\u00a0", "MEC"]) == [{"etiqueta": "MEC", "cantidad": 2}]
    _, parametros = condiciones_fondos(FiltrosAnalisis(organismo="MEC"))
    assert parametros == ["mec"]


def test_etiquetas_organismo_variante_mas_frecuente():
    etiquetas = etiquetas_organismo({"ANII": 3, "anii": 1, " ANII  ": 2, "Ute": 1, "UTE": 1, "": 4, None: 1})
    # "ANII" y " ANII  " son la misma variante una vez colapsada (5 contra 1)
    assert etiquetas == {"anii": "ANII", "ute": "UTE"}


def test_por_organismo_agrupa_variantes():
    serie = por_organismo(["ANII", "anii", "ANII  ", "Agencia  Nacional", "agencia nacional", "  ", None])
    assert serie == [
        {"etiqueta": "ANII", "cantidad": 3},
        {"etiqueta": "Agencia Nacional", "cantidad": 2},
        {"etiqueta": "Sin dato", "cantidad": 2},
    ]


def test_anio_de_solo_entre_1900_y_2100():
    assert anio_de("Proyecto 0007") is None
    assert anio_de("Expediente 4521") is None
    assert anio_de("1899") is None
    assert anio_de("1900") == 1900
    assert anio_de("2100") == 2100
    assert anio_de("Exp. 0042 de 2019") == 2019


def test_rellenar_por_anio_ignora_anios_invalidos_y_tiene_tope():
    serie = rellenar_periodos({"0201": 5, "2025": 1}, "anio")
    assert serie == [{"periodo": "2025", "cantidad": 1}]

    serie = rellenar_periodos({"1900": 1, "2025": 1}, "anio")
    assert len(serie) == analisis_service.LIMITE_ANIOS
    assert serie[0]["periodo"] == "1976"
    assert serie[-1] == {"periodo": "2025", "cantidad": 1}


def test_rellenar_por_mes_ignora_anios_invalidos():
    assert rellenar_periodos({"0201-03": 2, "2025-01": 1}, "mes") == [{"periodo": "2025-01", "cantidad": 1}]


def test_fondos_con_fecha_invalida_van_a_sin_fecha():
    fila = {
        "institucion": "ANII", "estado": "Abierta", "fecha_apertura": date(201, 3, 1),
        "fecha_cierre": date(2025, 5, 1), "titulo": "", "descripcion": "", "beneficiarios": "",
        "financiamiento": "",
    }
    fondos = analisis_service.armar_fondos([fila])
    assert fondos["por_anio_apertura"] == [{"etiqueta": "Sin fecha", "cantidad": 1}]

    tendencias = analisis_service.armar_tendencias([fila], [], [], "anio")
    assert tendencias["fondos_por_apertura"] == [{"periodo": "2025", "cantidad": 0}]
    assert tendencias["fondos_por_cierre"] == [{"periodo": "2025", "cantidad": 1}]


def test_tendencias_creado_en_hora_de_uruguay():
    investigadores = [
        # 01:00 UTC del 1/1 es todavía 31/12 en Uruguay
        {"creado": datetime(2026, 1, 1, 1, tzinfo=timezone.utc)},
        {"creado": datetime(2026, 1, 1, 4, tzinfo=timezone.utc)},
    ]
    tendencias = analisis_service.armar_tendencias([], [], investigadores, "anio")
    assert tendencias["investigadores_incorporados"] == [
        {"periodo": "2025", "cantidad": 1},
        {"periodo": "2026", "cantidad": 1},
    ]


def test_tendencias_apertura_y_cierre_comparten_periodos():
    fondos = [
        {"fecha_apertura": date(2010, 1, 1), "fecha_cierre": None},
        {"fecha_apertura": date(2024, 6, 1), "fecha_cierre": date(2026, 3, 1)},
    ]
    tendencias = analisis_service.armar_tendencias(fondos, [], [], "mes")

    apertura = [p["periodo"] for p in tendencias["fondos_por_apertura"]]
    cierre = [p["periodo"] for p in tendencias["fondos_por_cierre"]]
    assert apertura == cierre
    assert len(apertura) == 120
    assert apertura[0] == "2016-04"
    assert apertura[-1] == "2026-03"
    assert sum(p["cantidad"] for p in tendencias["fondos_por_apertura"]) == 1
    assert sum(p["cantidad"] for p in tendencias["fondos_por_cierre"]) == 1


def test_tendencias_informa_filtros_aplicados():
    tendencias = analisis_service.armar_tendencias([], [], [], "anio")
    assert tendencias["filtros_aplicados"] == {
        "fondos": ["organismo", "tematica", "estado", "periodo"],
        "proyectos": ["tematica", "periodo"],
        "investigadores": ["organismo", "tematica"],
    }


def test_condiciones_fondos_sin_filtros_solo_visibles():
    sql, parametros = condiciones_fondos(FiltrosAnalisis())
    assert parametros == []
    assert "%s" not in sql


def test_filtros_como_dict():
    filtros = FiltrosAnalisis(tematica="Salud", desde=date(2024, 3, 1))
    assert filtros.como_dict() == {
        "organismo": None,
        "tematica": "Salud",
        "estado": None,
        "desde": "2024-03-01",
        "hasta": None,
    }


# --- Router ---

class ServicioFalso:
    def __init__(self):
        self.llamadas = []

    def obtener_opciones(self):
        self.llamadas.append(("opciones",))
        return {"organismos": [], "tematicas": [], "estados": [], "sector_economico": {}}

    def _seccion(self, nombre):
        def funcion(filtros, *args):
            self.llamadas.append((nombre, filtros, *args))
            return {"seccion": nombre}
        return funcion


@pytest.fixture
def servicio(monkeypatch):
    falso = ServicioFalso()
    monkeypatch.setattr(analisis_service, "obtener_opciones", falso.obtener_opciones)
    for nombre in ("resumen", "fondos", "investigadores", "proyectos", "tendencias"):
        monkeypatch.setattr(analisis_service, f"obtener_{nombre}", falso._seccion(nombre))
    return falso


@pytest.mark.parametrize("ruta", RUTAS)
def test_rutas_exigen_token(ruta, servicio):
    respuesta = client_sin_token.get(ruta)
    assert respuesta.status_code == 401
    assert servicio.llamadas == []


def test_sin_token_gana_aunque_el_filtro_sea_invalido(servicio):
    respuesta = client_sin_token.get("/api/analisis/fondos?tematica=Cocina")
    assert respuesta.status_code == 401


@pytest.mark.parametrize("ruta", RUTAS[1:])
def test_tematica_invalida(ruta, servicio):
    respuesta = client.get(ruta, params={"tematica": "Cocina"})
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "Elegí una temática válida."
    assert servicio.llamadas == []


def test_estado_invalido(servicio):
    respuesta = client.get("/api/analisis/fondos", params={"estado": "Suspendida"})
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "Elegí un estado válido."


@pytest.mark.parametrize(
    "params",
    [
        {"desde": "2025-01-01", "hasta": "2024-01-01"},
        {"desde": "31/12/2024"},
        {"hasta": "2024-02-30"},
    ],
)
def test_periodo_invalido(params, servicio):
    respuesta = client.get("/api/analisis/resumen", params=params)
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "El período es inválido."
    assert servicio.llamadas == []


def test_agrupar_invalido(servicio):
    respuesta = client.get("/api/analisis/tendencias", params={"agrupar": "semana"})
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "Agrupación inválida."


def test_filtros_llegan_al_service(servicio):
    respuesta = client.get(
        "/api/analisis/fondos",
        params={
            "organismo": "  ANII  ",
            "tematica": "salud",
            "estado": "proxima",
            "desde": "2024-01-01",
            "hasta": "2024-12-31",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"seccion": "fondos"}
    assert servicio.llamadas == [(
        "fondos",
        FiltrosAnalisis(
            organismo="ANII",
            tematica="Salud",
            estado="Próxima",
            desde=date(2024, 1, 1),
            hasta=date(2024, 12, 31),
        ),
    )]


def test_filtros_vacios_son_none(servicio):
    respuesta = client.get("/api/analisis/proyectos", params={"tematica": "", "desde": ""})
    assert respuesta.status_code == 200
    assert servicio.llamadas == [("proyectos", FiltrosAnalisis())]


def test_tendencias_agrupar(servicio):
    assert client.get("/api/analisis/tendencias").status_code == 200
    assert client.get("/api/analisis/tendencias", params={"agrupar": "mes"}).status_code == 200
    assert [llamada[2] for llamada in servicio.llamadas] == ["anio", "mes"]


# --- Service con base falsa ---

class CursorFalso:
    """to_regclass devuelve None si la tabla no está en `tablas`; los SELECT devuelven `filas`."""

    def __init__(self, tablas=(), filas=None):
        self.tablas = set(tablas)
        self.filas = filas or {}
        self.ejecutadas = []
        self._siguiente = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, parametros=None):
        self.ejecutadas.append((sql, parametros))
        if "to_regclass" in sql:
            nombre = parametros[0].removeprefix("public.")
            self._siguiente = (nombre,) if nombre in self.tablas else (None,)
        elif "GROUP BY institucion" in sql:
            self._siguiente = self.filas.get("organismos", [])
        else:
            tabla = next(t for t in ("convocatoria", "investigadores", "proyectos") if f"FROM {t}" in sql)
            self._siguiente = self.filas.get(tabla, [])

    def fetchone(self):
        return self._siguiente

    def fetchall(self):
        return self._siguiente


class ConexionFalsa:
    def __init__(self, cursor):
        self._cursor = cursor
        self.cerrada = False

    def cursor(self):
        return self._cursor

    def close(self):
        self.cerrada = True


class BaseFalsa:
    def __init__(self, cursor):
        self.cursor = cursor
        self.conexiones = []

    def conectar(self):
        conexion = ConexionFalsa(self.cursor)
        self.conexiones.append(conexion)
        return conexion


HOY = date(2026, 10, 26)

FONDOS = [
    # institucion, estado, apertura, cierre, titulo, descripcion, beneficiarios, financiamiento
    ("ANII", "Abierta", date(2026, 9, 1), date(2026, 11, 10), "Innovación en salud", "x", "", "USD 10.000"),
    ("ANII ", "Cerrada", date(2025, 3, 1), date(2025, 4, 1), "Becas", "Educación superior", None, None),
    ("UTEC", "Próxima", None, date(2027, 1, 1), "Fondo", "Alimentación saludable", "", ""),
]
INVESTIGADORES = [
    ("Universidad de la República/ Facultad de Ingeniería / Uruguay", "Doctor en Ingeniería",
     "Energía solar\nRedes\n", "Nivel I", "Activo", datetime(2025, 5, 3, tzinfo=timezone.utc)),
    ("Instituto Pasteur", "Licenciada en Biología", "Salud pública", None, None,
     datetime(2025, 7, 1, 12, tzinfo=timezone.utc)),
]
PROYECTOS = [
    ("Tecnología educativa", "En curso", "2024", "Educación"),
    ("Agua", "Finalizado", "2021", ""),
    ("Sin año", "En curso", "s/d", ""),
]


@pytest.fixture
def sin_cache(monkeypatch):
    monkeypatch.setattr(analisis_service.cache_service, "leer", lambda clave: None)
    monkeypatch.setattr(analisis_service.cache_service, "guardar", lambda clave, valor: None)


def _base(monkeypatch, tablas, filas=None):
    base = BaseFalsa(CursorFalso(tablas, filas))
    monkeypatch.setattr(analisis_service, "get_connection", base.conectar)
    monkeypatch.setattr(analisis_service, "hoy_uruguay", lambda: HOY)
    return base


def test_tabla_faltante_no_disponible(monkeypatch, sin_cache):
    base = _base(monkeypatch, tablas=())

    fondos = analisis_service.obtener_fondos(FiltrosAnalisis())

    assert fondos["disponible"] is False
    assert fondos["total"] == 0
    assert fondos["por_organismo"] == []
    assert fondos["por_tematica"] == []
    assert fondos["filtros_aplicados"] == ["organismo", "tematica", "estado", "periodo"]
    assert fondos["por_sector_economico"]["disponible"] is False
    # No llegó a consultar la tabla
    assert all("to_regclass" in sql for sql, _ in base.cursor.ejecutadas)
    assert all(c.cerrada for c in base.conexiones)

    assert analisis_service.obtener_investigadores(FiltrosAnalisis())["disponible"] is False
    assert analisis_service.obtener_proyectos(FiltrosAnalisis())["disponible"] is False

    resumen = analisis_service.obtener_resumen(FiltrosAnalisis())
    assert resumen["fondos"]["disponible"] is False
    assert resumen["fondos"]["total"] == 0

    tendencias = analisis_service.obtener_tendencias(FiltrosAnalisis(), "anio")
    assert tendencias["disponible"] == {"fondos": False, "proyectos": False, "investigadores": False}
    assert tendencias["fondos_por_apertura"] == []


def test_opciones_sin_tabla_convocatoria(monkeypatch, sin_cache):
    _base(monkeypatch, tablas=())

    def no_deberia_llamarse():
        raise AssertionError("consultó convocatoria sin que exista")

    monkeypatch.setattr(analisis_service.alerta_service, "instituciones_disponibles", no_deberia_llamarse)

    opciones = analisis_service.obtener_opciones()
    assert opciones["organismos"] == []
    assert opciones["estados"] == ["Abierta", "Próxima", "Cerrada", "Otro", "Sin estado"]
    assert opciones["sector_economico"]["disponible"] is False


def test_opciones_organismos_visibles_y_sin_duplicados(monkeypatch, sin_cache):
    base = _base(
        monkeypatch,
        tablas={"convocatoria"},
        filas={"organismos": [("ANII", 4), ("anii", 1), ("Agencia  Nacional", 1), ("UTEC", 2), ("utec", 2)]},
    )

    def no_deberia_llamarse():
        raise AssertionError("usa la lista de RF005, que incluye convocatorias no visibles")

    monkeypatch.setattr(analisis_service.alerta_service, "instituciones_disponibles", no_deberia_llamarse)

    opciones = analisis_service.obtener_opciones()

    assert opciones["organismos"] == ["Agencia Nacional", "ANII", "UTEC"]
    sql, _ = base.cursor.ejecutadas[-1]
    assert CONDICION_VISIBLE in sql


def test_fondos_con_datos(monkeypatch, sin_cache):
    _base(monkeypatch, tablas={"convocatoria"}, filas={"convocatoria": FONDOS})

    fondos = analisis_service.obtener_fondos(FiltrosAnalisis())

    assert fondos["disponible"] is True
    assert fondos["total"] == 3
    assert fondos["por_organismo"][0] == {"etiqueta": "ANII", "cantidad": 2}
    assert {"etiqueta": "Salud", "cantidad": 1} in fondos["por_tematica"]
    assert fondos["por_tematica"][-1] == {"etiqueta": "Sin clasificar", "cantidad": 1}
    assert fondos["por_anio_apertura"] == [
        {"etiqueta": "2025", "cantidad": 1},
        {"etiqueta": "2026", "cantidad": 1},
        {"etiqueta": "Sin fecha", "cantidad": 1},
    ]
    assert fondos["financiamiento"] == {"informado": 1, "sin_informar": 2}


def test_fondos_filtra_tematica_y_estado(monkeypatch, sin_cache):
    _base(monkeypatch, tablas={"convocatoria"}, filas={"convocatoria": FONDOS})

    assert analisis_service.obtener_fondos(FiltrosAnalisis(tematica="Salud"))["total"] == 1
    assert analisis_service.obtener_fondos(FiltrosAnalisis(estado="Próxima"))["total"] == 1


def test_resumen_con_datos(monkeypatch, sin_cache):
    _base(
        monkeypatch,
        tablas={"convocatoria", "investigadores", "proyectos"},
        filas={"convocatoria": FONDOS, "investigadores": INVESTIGADORES, "proyectos": PROYECTOS},
    )

    resumen = analisis_service.obtener_resumen(FiltrosAnalisis())

    assert resumen["fondos"]["abiertos"] == 1
    assert resumen["fondos"]["cierran_30_dias"] == 1
    assert resumen["fondos"]["organismos"] == 2
    assert resumen["investigadores"]["instituciones"] == 2
    assert resumen["investigadores"]["con_nivel_sni"] == 1
    assert resumen["proyectos"] == {
        "disponible": True,
        "filtros_aplicados": ["tematica", "periodo"],
        "total": 3,
        "en_curso": 2,
        "finalizados": 1,
    }


def test_proyectos_con_periodo_excluye_sin_anio(monkeypatch, sin_cache):
    _base(monkeypatch, tablas={"proyectos"}, filas={"proyectos": PROYECTOS})

    proyectos = analisis_service.obtener_proyectos(
        FiltrosAnalisis(desde=date(2022, 1, 1), hasta=date(2025, 12, 31))
    )
    assert proyectos["total"] == 1
    assert proyectos["por_anio"] == [{"etiqueta": "2024", "cantidad": 1}]


def test_investigadores_organismo_parcial(monkeypatch, sin_cache):
    base = _base(monkeypatch, tablas={"investigadores"}, filas={"investigadores": INVESTIGADORES})

    investigadores = analisis_service.obtener_investigadores(FiltrosAnalisis(organismo="100%_real"))

    sql, parametros = base.cursor.ejecutadas[-1]
    assert "ILIKE %s" in sql
    assert parametros == ["%100\\%\\_real%"]
    assert investigadores["lineas_investigacion"] == {"total": 3, "promedio_por_investigador": 1.5}
    assert investigadores["por_formacion"] == [
        {"etiqueta": "Doctorado", "cantidad": 1},
        {"etiqueta": "Grado", "cantidad": 1},
    ]


def test_tendencias_rellena(monkeypatch, sin_cache):
    _base(
        monkeypatch,
        tablas={"convocatoria", "investigadores", "proyectos"},
        filas={"convocatoria": FONDOS, "investigadores": INVESTIGADORES, "proyectos": PROYECTOS},
    )

    tendencias = analisis_service.obtener_tendencias(FiltrosAnalisis(), "mes")

    assert tendencias["agrupar"] == "mes"
    assert tendencias["investigadores_incorporados"] == [
        {"periodo": "2025-05", "cantidad": 1},
        {"periodo": "2025-06", "cantidad": 0},
        {"periodo": "2025-07", "cantidad": 1},
    ]
    assert [p["periodo"] for p in tendencias["proyectos_por_anio"]] == ["2021", "2022", "2023", "2024"]
    # Eje común: arranca en la primera apertura (2025-03) aunque el primer cierre sea 2025-04
    assert tendencias["fondos_por_cierre"][0] == {"periodo": "2025-03", "cantidad": 0}
    assert [p["periodo"] for p in tendencias["fondos_por_cierre"]] == [
        p["periodo"] for p in tendencias["fondos_por_apertura"]
    ]


def test_cache_evita_segunda_consulta(monkeypatch):
    guardado = {}
    monkeypatch.setattr(analisis_service.cache_service, "leer", guardado.get)
    monkeypatch.setattr(analisis_service.cache_service, "guardar", guardado.__setitem__)
    base = _base(monkeypatch, tablas={"convocatoria"}, filas={"convocatoria": FONDOS})

    primera = analisis_service.obtener_fondos(FiltrosAnalisis(tematica="Salud"))
    consultas = len(base.cursor.ejecutadas)
    segunda = analisis_service.obtener_fondos(FiltrosAnalisis(tematica="Salud"))

    assert segunda == primera
    assert len(base.cursor.ejecutadas) == consultas
    assert len(base.conexiones) == 1

    # Otros filtros, otra clave
    analisis_service.obtener_fondos(FiltrosAnalisis(tematica="Energía"))
    assert len(base.conexiones) == 2
    assert all(clave.startswith("cache:analisis:fondos:") for clave in guardado)
