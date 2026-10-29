"""Tests extra de RF006 (QA): contrato con el front, casos borde y middleware real de app.main.

Los marcados con xfail(strict=True) documentan bugs conocidos: cuando se arreglen, el test
empieza a pasar, pytest lo marca como XPASS → falla, y hay que sacar el xfail.
"""

from datetime import date, datetime, timedelta, timezone

import pytest
import redis
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import obtener_usuario_actual
from app.routers import analisis
from app.services import analisis_service, cache_service, uso_service
from app.services.analisis_service import (
    FiltrosAnalisis,
    anio_de,
    armar_fondos,
    armar_investigadores,
    armar_proyectos,
    armar_tendencias,
    rellenar_periodos,
)

USUARIO = {"sub": "usuario-1", "realm_access": {"roles": []}}


# --- Contrato con Frontend/lib/analisis.ts ---
# Si cambia una clave acá, hay que cambiar el tipo TypeScript (y al revés).

CLAVES_FONDOS = {
    "disponible", "filtros_aplicados", "total", "por_organismo", "por_tematica",
    "por_estado", "por_anio_apertura", "por_sector_economico", "financiamiento",
    "tematica_multiple",
}
CLAVES_INVESTIGADORES = {
    "disponible", "filtros_aplicados", "total", "por_institucion", "por_nivel_sni",
    "por_categoria_sni", "por_formacion", "por_area_tematica", "lineas_investigacion",
}
CLAVES_PROYECTOS = {
    "disponible", "filtros_aplicados", "total", "por_estado", "por_anio", "por_tematica",
    "por_organismo",
}
CLAVES_TENDENCIAS = {
    "agrupar", "fondos_por_apertura", "fondos_por_cierre", "proyectos_por_anio",
    "investigadores_incorporados", "disponible", "filtros_aplicados",
}


def test_contrato_secciones_con_y_sin_datos():
    for armar, claves in (
        (armar_fondos, CLAVES_FONDOS),
        (armar_investigadores, CLAVES_INVESTIGADORES),
        (armar_proyectos, CLAVES_PROYECTOS),
    ):
        con_datos = analisis_service._seccion([], armar)
        sin_tabla = analisis_service._seccion(None, armar)
        assert set(con_datos) == claves
        assert set(sin_tabla) == claves
        assert sin_tabla["disponible"] is False
        assert sin_tabla["total"] == 0
        # filtros_aplicados no se vacía aunque la sección no esté disponible
        assert sin_tabla["filtros_aplicados"] == con_datos["filtros_aplicados"]

    fondos = armar_fondos([])
    assert fondos["por_sector_economico"]["disponible"] is False
    assert fondos["por_sector_economico"]["motivo"]
    assert set(fondos["financiamiento"]) == {"informado", "sin_informar"}
    assert armar_proyectos([])["por_organismo"]["disponible"] is False
    assert set(armar_investigadores([])["lineas_investigacion"]) == {"total", "promedio_por_investigador"}

    tendencias = armar_tendencias(None, None, None, "anio")
    assert set(tendencias) == CLAVES_TENDENCIAS
    assert tendencias["disponible"] == {"fondos": False, "proyectos": False, "investigadores": False}
    assert tendencias["filtros_aplicados"] == {
        "fondos": ["organismo", "tematica", "estado", "periodo"],
        "proyectos": ["tematica", "periodo"],
        "investigadores": ["organismo", "tematica"],
    }


def test_filtros_aplicados_son_claves_del_front():
    claves_front = {"organismo", "tematica", "estado", "periodo"}
    for lista in (
        analisis_service.FILTROS_FONDOS,
        analisis_service.FILTROS_INVESTIGADORES,
        analisis_service.FILTROS_PROYECTOS,
    ):
        assert set(lista) <= claves_front


def test_estados_iguales_al_front():
    # Frontend/lib/analisis.ts: ESTADOS
    assert list(analisis_service.ESTADOS) == ["Abierta", "Próxima", "Cerrada", "Otro", "Sin estado"]


# --- Armado con filas variadas ---

def _fondo(**campos):
    base = {
        "institucion": None, "estado": None, "fecha_apertura": None, "fecha_cierre": None,
        "titulo": None, "descripcion": None, "beneficiarios": None, "financiamiento": None,
    }
    return {**base, **campos}


def test_armar_fondos_campos_nulos_y_sin_dato_al_final():
    filas = [
        _fondo(institucion="ANII", estado="Abierta", fecha_apertura=date(2025, 1, 1),
               titulo="Fondo de Salud", financiamiento="USD 10"),
        _fondo(institucion="  ", estado=None, descripcion="educación"),
        _fondo(institucion=None, estado="raro", financiamiento="   "),
    ]

    fondos = armar_fondos(filas)

    assert fondos["total"] == 3
    assert fondos["por_organismo"] == [
        {"etiqueta": "ANII", "cantidad": 1},
        {"etiqueta": "Sin dato", "cantidad": 2},
    ]
    assert fondos["por_estado"][-1] == {"etiqueta": "Sin estado", "cantidad": 1}
    assert fondos["por_anio_apertura"] == [
        {"etiqueta": "2025", "cantidad": 1},
        {"etiqueta": "Sin fecha", "cantidad": 2},
    ]
    assert fondos["por_tematica"] == [
        {"etiqueta": "Educación", "cantidad": 1},
        {"etiqueta": "Salud", "cantidad": 1},
        {"etiqueta": "Sin clasificar", "cantidad": 1},
    ]
    # Solo espacios no cuenta como financiamiento informado
    assert fondos["financiamiento"] == {"informado": 1, "sin_informar": 2}


def test_armar_fondos_top_con_otros_antes_de_sin_dato():
    filas = [_fondo(institucion=f"Org {i:02d}") for i in range(20)] + [_fondo(institucion=None)]

    serie = armar_fondos(filas)["por_organismo"]

    assert len(serie) == 17
    assert serie[-2] == {"etiqueta": "Otros", "cantidad": 5}
    assert serie[-1] == {"etiqueta": "Sin dato", "cantidad": 1}
    assert sum(p["cantidad"] for p in serie) == 21


def test_armar_investigadores_sin_filas_no_divide_por_cero():
    inv = armar_investigadores([])
    assert inv["lineas_investigacion"] == {"total": 0, "promedio_por_investigador": 0.0}


def test_tendencias_creado_timestamptz_a_periodo():
    inv = [{"creado": datetime(2025, 3, 10, 12, tzinfo=timezone.utc)}, {"creado": None}]
    t = armar_tendencias([], [], inv, "mes")
    assert t["investigadores_incorporados"] == [{"periodo": "2025-03", "cantidad": 1}]


def test_tendencias_creado_usa_dia_de_uruguay():
    # 2025-04-01 01:00 UTC es 31/03 22:00 en Uruguay
    inv = [{"creado": datetime(2025, 4, 1, 1, tzinfo=timezone.utc)}]
    t = armar_tendencias([], [], inv, "mes")
    assert t["investigadores_incorporados"] == [{"periodo": "2025-03", "cantidad": 1}]


# --- Bugs: series por año sin tope ---

def test_rellenar_periodos_por_anio_tiene_tope():
    serie = rellenar_periodos({"0201": 1, "2025": 1}, "anio")
    assert len(serie) <= analisis_service.LIMITE_MESES


def test_anio_de_descarta_numeros_que_no_son_anios():
    assert anio_de("Proyecto 0007") is None
    assert anio_de("Expediente 4521") is None


# --- Router: normalización de filtros ---

app = FastAPI()
app.include_router(analisis.router)
app.dependency_overrides[obtener_usuario_actual] = lambda: USUARIO
client = TestClient(app)


@pytest.fixture
def capturados(monkeypatch):
    recibidos = []

    def falso(f):
        recibidos.append(f)
        return {"ok": True}

    monkeypatch.setattr(analisis_service, "obtener_fondos", falso)
    return recibidos


def test_router_normaliza_tematica_y_estado_sin_tildes(capturados):
    r = client.get("/api/analisis/fondos", params={"tematica": "EDUCACION", "estado": "proxima"})
    assert r.status_code == 200
    assert capturados[0].tematica == "Educación"
    assert capturados[0].estado == "Próxima"


def test_router_organismo_largo_400(capturados):
    r = client.get("/api/analisis/fondos", params={"organismo": "x" * 201})
    assert r.status_code == 400
    assert capturados == []


def test_router_organismo_colapsa_espacios(capturados):
    r = client.get("/api/analisis/fondos", params={"organismo": "  Agencia \t Nacional  "})
    assert r.status_code == 200
    assert capturados[0].organismo == "Agencia Nacional"


def test_router_mismo_dia_desde_hasta_es_valido(capturados):
    r = client.get("/api/analisis/fondos", params={"desde": "2025-05-01", "hasta": "2025-05-01"})
    assert r.status_code == 200
    assert capturados[0].desde == capturados[0].hasta == date(2025, 5, 1)


@pytest.mark.parametrize("fecha", ["2025-02-30", "01/05/2025", "2025-5-1x"])
def test_router_fecha_inexistente_400(capturados, fecha):
    r = client.get("/api/analisis/fondos", params={"desde": fecha})
    assert r.status_code == 400
    assert r.json()["detail"] == "El período es inválido."


# --- Redis caído: la analítica sigue funcionando ---

class RedisCaido:
    def get(self, *args, **kwargs):
        raise redis.ConnectionError("caído")

    def set(self, *args, **kwargs):
        raise redis.ConnectionError("caído")


def test_redis_caido_no_rompe(monkeypatch):
    monkeypatch.setattr(cache_service, "_redis", lambda: RedisCaido())
    llamadas = []

    def calcular():
        llamadas.append(1)
        return {"total": 3}

    assert analisis_service._con_cache("fondos", {"a": 1}, calcular) == {"total": 3}
    assert llamadas == [1]


# --- Middleware real de app.main ---

@pytest.fixture
def app_main(monkeypatch):
    import app.main as main

    eventos = []
    monkeypatch.setattr(uso_service, "registrar_evento", lambda tipo, sub: eventos.append((tipo, sub)))
    monkeypatch.setattr(analisis_service, "obtener_resumen", lambda f: {"ok": True})
    monkeypatch.setitem(main.app.dependency_overrides, obtener_usuario_actual, lambda: USUARIO)
    return TestClient(main.app), eventos


def test_main_registra_analisis(app_main):
    cliente, eventos = app_main
    r = cliente.get("/api/analisis/resumen")
    assert r.status_code == 200
    assert eventos == [("analisis_datos", None)]


def test_main_no_registra_options_ni_metrics(app_main):
    cliente, eventos = app_main
    cliente.options(
        "/api/analisis/resumen",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    cliente.get("/metrics")
    assert eventos == []


def test_main_registro_que_lanza_no_cambia_la_respuesta(app_main, monkeypatch):
    cliente, _ = app_main

    def explota(tipo, sub):
        raise RuntimeError("base caída")

    monkeypatch.setattr(uso_service, "registrar_evento", explota)
    r = cliente.get("/api/analisis/resumen")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


# --- resumen_uso: límites del día en hora de Uruguay ---

def test_resumen_uso_limites_en_hora_de_uruguay(monkeypatch):
    consultas = []

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, sql, params=None):
            consultas.append((sql, params))
            self._r = [("evento_uso",)] if "to_regclass" in sql and "evento_uso" in params[0] else [(None,)]
            if "COUNT(DISTINCT" in sql:
                self._r = [(0, 0)]
            elif "GROUP BY" in sql:
                self._r = []

        def fetchone(self):
            return self._r[0]

        def fetchall(self):
            return self._r

    class Conn:
        def cursor(self):
            return Cursor()

        def close(self):
            pass

    monkeypatch.setattr(uso_service, "get_connection", lambda: Conn())
    uso_service.resumen_uso(date(2026, 10, 24), date(2026, 10, 25))

    inicio, fin = next(p for s, p in consultas if "COUNT(DISTINCT" in s)
    assert inicio.isoformat() == "2026-10-24T00:00:00-03:00"
    assert fin.isoformat() == "2026-10-26T00:00:00-03:00"
    assert inicio.utcoffset() == timedelta(hours=-3)


# --- clave_organismo (Python) vs CLAVE_ORGANISMO_SQL (Postgres) ---

# Espacios que la clave tiene que unificar, armados SIN mirar la regex del service: los que
# Unicode/Python considera espacio (str.isspace) más los invisibles U+200B y U+FEFF.
# Postgres con [[:space:]] / \s (glibc, en_US.utf8) NO incluye U+00A0, U+2007, U+202F, U+0085
# ni U+001C-U+001F; por eso la clase tiene que ser explícita. Se verificó contra postgres:16
# real (QA RF006, 3a vuelta) recorriendo todo el BMP: CLAVE_ORGANISMO_SQL y clave_organismo
# dan lo mismo en todos los code points salvo U+0130 y U+03A3 (diferencias de lower(), ver abajo).
_ESPACIOS = {chr(cp) for cp in range(0x10000) if chr(cp).isspace()} | {chr(0x200B), chr(0xFEFF)}


def _clave_como_postgres(texto):
    # COALESCE → reemplazar cada tramo de espacios por ' ' → btrim (solo ' ') → lower
    salida, en_espacio = [], False
    for caracter in texto or "":
        if caracter in _ESPACIOS:
            if not en_espacio:
                salida.append(" ")
            en_espacio = True
        else:
            salida.append(caracter)
            en_espacio = False
    return "".join(salida).strip(" ").lower()


def test_clase_espacios_es_la_del_sql():
    assert f"'{analisis_service.CLASE_ESPACIOS}'" in analisis_service.CLAVE_ORGANISMO_SQL
    # No usa \s: en Postgres no incluye el espacio duro
    assert r"\s" not in analisis_service.CLAVE_ORGANISMO_SQL


@pytest.mark.parametrize("texto", ["  ANII \t", "Agencia\n  Nacional", "ÓRGANO ÁÉÍÑ"])
def test_clave_organismo_igual_que_sql(texto):
    assert analisis_service.clave_organismo(texto) == _clave_como_postgres(texto)


def test_clave_organismo_espacio_duro_igual_que_sql():
    texto = "MEC "
    assert analisis_service.clave_organismo(texto) == _clave_como_postgres(texto)


@pytest.mark.parametrize("cp", sorted(ord(c) for c in _ESPACIOS))
def test_cada_espacio_unicode_se_unifica(cp):
    texto = f"A{chr(cp)}{chr(cp)}B"
    assert analisis_service.clave_organismo(texto) == _clave_como_postgres(texto) == "a b"


@pytest.mark.parametrize("cp", [0x2007, 0x00A0, 0x202F, 0x0085, 0x001C])
def test_espacios_que_postgres_no_reconoce_con_backslash_s(cp):
    # Por estos no alcanza \s en el SQL: tienen que estar en la clase explícita
    assert chr(cp) in _ESPACIOS
    assert analisis_service.PATRON_ESPACIOS.fullmatch(chr(cp))


def test_no_espacios_no_se_tocan():
    for texto in ("ANII", "O'Higgins", "100% Uruguay_x", "Ministerio de Educación y Cultura"):
        assert analisis_service.clave_organismo(texto) == texto.lower()
