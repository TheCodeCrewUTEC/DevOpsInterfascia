import asyncio
from datetime import date

import jwt
import psycopg2
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.background import BackgroundTask

from app.auth import obtener_usuario_actual
from app.database import connection
from app.routers import uso
from app.services import uso_service

USUARIO = {"sub": "usuario-1", "email": "ana@example.com"}
ADMIN = {**USUARIO, "realm_access": {"roles": ["admin"]}}
# Solo para firmar tokens de prueba; sub_sin_verificar no mira la firma
CLAVE_PRUEBA = "clave-de-prueba-de-al-menos-32-bytes"


@pytest.fixture(autouse=True)
def sin_pausa(monkeypatch):
    # El corte es estado del módulo: cada test arranca sin pausa
    monkeypatch.setattr(uso_service, "_pausado_hasta", 0.0)


# --- clasificar ---

@pytest.mark.parametrize(
    "metodo, ruta, query, status, esperado",
    [
        ("GET", "/api/convocatorias/", {"buscar": "agua"}, 200, "busqueda_repositorio"),
        ("GET", "/api/convocatorias", {"buscar": "agua"}, 200, "busqueda_repositorio"),
        ("GET", "/api/convocatorias/", {"buscar": "   "}, 200, "consulta_repositorio"),
        ("GET", "/api/convocatorias/", {"buscar": ""}, 200, "consulta_repositorio"),
        ("GET", "/api/convocatorias/", {"limit": "50"}, 200, "consulta_repositorio"),
        ("get", "/api/convocatorias/", {}, 200, "consulta_repositorio"),
        ("GET", "/api/convocatorias", {}, 307, None),
        ("GET", "/api/convocatorias/12", {}, 200, "detalle_fondo"),
        ("GET", "/api/convocatorias/12/", {}, 200, "detalle_fondo"),
        ("GET", "/api/convocatorias/12", {}, 404, None),
        ("GET", "/api/convocatorias/abc", {}, 200, None),
        ("GET", "/api/convocatorias/12/documentos", {}, 200, None),
        ("POST", "/api/convocatorias/", {}, 200, None),
        ("POST", "/formularios/jobs", {}, 200, "consultor_formulario"),
        ("GET", "/formularios/jobs", {}, 200, None),
        ("POST", "/formularios/jobs/7/confirmar", {}, 200, "consultor_confirmacion"),
        ("POST", "/formularios/jobs/7/confirmar", {}, 409, None),
        ("GET", "/api/analisis/resumen", {}, 200, "analisis_datos"),
        ("GET", "/api/analisis/tendencias/", {}, 200, "analisis_datos"),
        ("GET", "/api/analisis/opciones", {}, 200, None),
        ("POST", "/api/alertas/suscripciones", {}, 201, "alerta_suscripcion"),
        ("POST", "/api/alertas/suscripciones", {}, 400, None),
        ("GET", "/api/alertas/suscripciones", {}, 200, None),
        ("GET", "/api/alertas/notificaciones", {}, 200, "alertas_consulta"),
        ("PUT", "/api/perfil", {}, 200, "perfil_actualizacion"),
        ("GET", "/api/perfil", {}, 200, None),
        ("GET", "/api/proyectos/", {"buscar": "agua"}, 200, None),
        ("GET", "/api/investigadores/", {"buscar": "agua"}, 200, None),
        ("GET", "/metrics", {}, 200, None),
        ("OPTIONS", "/api/convocatorias/", {}, 200, None),
    ],
)
def test_clasificar(metodo, ruta, query, status, esperado):
    assert uso_service.clasificar(metodo, ruta, query, status) == esperado


def test_todas_las_claves_tienen_etiqueta():
    claves = {
        uso_service.clasificar("GET", "/api/convocatorias", {"buscar": "x"}, 200),
        uso_service.clasificar("GET", "/api/convocatorias", {}, 200),
        uso_service.clasificar("GET", "/api/convocatorias/1", {}, 200),
        uso_service.clasificar("POST", "/formularios/jobs/1/confirmar", {}, 200),
        uso_service.clasificar("GET", "/api/analisis/fondos", {}, 200),
        *uso_service.RUTAS_FIJAS.values(),
    }
    assert claves == set(uso_service.FUNCIONALIDADES)


# --- sub_sin_verificar ---

def test_sub_sin_verificar_lee_el_sub_sin_firma():
    token = jwt.encode({"sub": "abc-123"}, CLAVE_PRUEBA, algorithm="HS256")
    assert uso_service.sub_sin_verificar(f"Bearer {token}") == "abc-123"
    assert uso_service.sub_sin_verificar(f"bearer {token}") == "abc-123"


@pytest.mark.parametrize(
    "authorization",
    [None, "", "Bearer", "Bearer ", "Bearer basura", "Basic dXN1YXJpbzpjbGF2ZQ=="],
)
def test_sub_sin_verificar_invalido(authorization):
    assert uso_service.sub_sin_verificar(authorization) is None


def test_sub_sin_verificar_sin_bearer():
    token = jwt.encode({"sub": "abc-123"}, CLAVE_PRUEBA, algorithm="HS256")
    assert uso_service.sub_sin_verificar(token) is None


def test_sub_sin_verificar_token_sin_sub():
    token = jwt.encode({"email": "a@b.com"}, CLAVE_PRUEBA, algorithm="HS256")
    assert uso_service.sub_sin_verificar(f"Bearer {token}") is None


def test_sub_sin_verificar_trunca_sub_largo():
    token = jwt.encode({"sub": "x" * 10_000}, CLAVE_PRUEBA, algorithm="HS256")
    assert uso_service.sub_sin_verificar(f"Bearer {token}") == "x" * 255


@pytest.mark.parametrize("sub", [123, ["a", "b"], {"id": "a"}, True, "   "])
def test_sub_sin_verificar_descarta_sub_que_no_es_texto(sub):
    token = jwt.encode({"sub": sub}, CLAVE_PRUEBA, algorithm="HS256")
    assert uso_service.sub_sin_verificar(f"Bearer {token}") is None


# --- Middleware ---

def _app_con_middleware():
    """App mínima con el mismo middleware que app/main.py."""

    app = FastAPI()

    @app.middleware("http")
    async def registrar_uso(request: Request, call_next):
        response = await call_next(request)
        try:
            uso_service.registrar_si_corresponde(request, response)
        except Exception:
            pass
        return response

    @app.get("/api/convocatorias/")
    def convocatorias(buscar: str | None = None):
        return {"items": []}

    @app.get("/api/convocatorias/{id}")
    def detalle(id: int):
        return JSONResponse({"detail": "Convocatoria no encontrada"}, status_code=404)

    return TestClient(app)


@pytest.fixture
def eventos(monkeypatch):
    registrados = []
    monkeypatch.delenv("REGISTRAR_USO", raising=False)
    monkeypatch.setattr(
        uso_service, "registrar_evento", lambda tipo, sub: registrados.append((tipo, sub))
    )
    return registrados


def test_middleware_registra_busqueda(eventos):
    token = jwt.encode({"sub": "usuario-9"}, CLAVE_PRUEBA, algorithm="HS256")
    response = _app_con_middleware().get(
        "/api/convocatorias/?buscar=agua", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    # Solo el tipo y el usuario: el término buscado no se guarda
    assert eventos == [("busqueda_repositorio", "usuario-9")]


def test_middleware_sin_token_registra_sin_usuario(eventos):
    _app_con_middleware().get("/api/convocatorias/")
    assert eventos == [("consulta_repositorio", None)]


def test_middleware_no_registra_404(eventos):
    response = _app_con_middleware().get("/api/convocatorias/5")
    assert response.status_code == 404
    assert eventos == []


def test_middleware_no_registra_redireccion(eventos):
    # El 307 hacia la ruta con barra no se cuenta; la request final sí, una sola vez
    response = _app_con_middleware().get("/api/convocatorias?buscar=agua")
    assert response.status_code == 200
    assert eventos == [("busqueda_repositorio", None)]


def test_middleware_deshabilitado(eventos, monkeypatch):
    monkeypatch.setenv("REGISTRAR_USO", "0")
    response = _app_con_middleware().get("/api/convocatorias/?buscar=agua")
    assert response.status_code == 200
    assert eventos == []


def test_middleware_si_registrar_falla_la_respuesta_sigue(monkeypatch):
    def falla(tipo, sub):
        raise RuntimeError("base caída")

    monkeypatch.delenv("REGISTRAR_USO", raising=False)
    monkeypatch.setattr(uso_service, "registrar_evento", falla)
    response = _app_con_middleware().get("/api/convocatorias/?buscar=agua")

    assert response.status_code == 200
    assert response.json() == {"items": []}


class RequestFalsa:
    method = "GET"
    headers = {}
    query_params = {"buscar": "agua"}

    class url:
        path = "/api/convocatorias/"


def test_registro_va_como_tarea_en_segundo_plano(eventos):
    # El registro no corre antes de responder: queda en response.background
    response = JSONResponse({"items": []})
    uso_service.registrar_si_corresponde(RequestFalsa(), response)

    assert eventos == []
    assert isinstance(response.background, BackgroundTask)

    asyncio.run(response.background())
    assert eventos == [("busqueda_repositorio", None)]


def test_registro_respeta_la_tarea_existente(eventos):
    otras = []
    response = JSONResponse({"items": []}, background=BackgroundTask(otras.append, "propia"))
    uso_service.registrar_si_corresponde(RequestFalsa(), response)

    asyncio.run(response.background())
    assert otras == ["propia"]
    assert eventos == [("busqueda_repositorio", None)]


def test_middleware_con_tarea_propia_de_la_ruta(eventos):
    otras = []
    app = FastAPI()

    @app.middleware("http")
    async def registrar_uso(request: Request, call_next):
        response = await call_next(request)
        uso_service.registrar_si_corresponde(request, response)
        return response

    @app.get("/api/convocatorias/")
    def convocatorias():
        return JSONResponse({"items": []}, background=BackgroundTask(otras.append, "propia"))

    response = TestClient(app).get("/api/convocatorias/?buscar=agua")

    assert response.status_code == 200
    assert otras == ["propia"]
    assert eventos == [("busqueda_repositorio", None)]


def test_registro_que_lanza_en_segundo_plano_no_propaga(monkeypatch):
    def falla(tipo, sub):
        raise RuntimeError("base caída")

    monkeypatch.delenv("REGISTRAR_USO", raising=False)
    monkeypatch.setattr(uso_service, "registrar_evento", falla)
    response = JSONResponse({"items": []})
    uso_service.registrar_si_corresponde(RequestFalsa(), response)

    assert asyncio.run(response.background()) is None


@pytest.mark.parametrize(
    "valor, esperado",
    [(None, 5), ("", 5), ("5s", 5), ("abc", 5), ("2.5", 5), (" 3 ", 3), ("10", 10), ("0", 1), ("-4", 1)],
)
def test_segundos_conexion_nunca_lanza(monkeypatch, valor, esperado):
    if valor is None:
        monkeypatch.delenv("DB_CONNECT_TIMEOUT", raising=False)
    else:
        monkeypatch.setenv("DB_CONNECT_TIMEOUT", valor)
    assert connection.segundos_conexion() == esperado


def test_get_connection_con_timeout_invalido_no_lanza(monkeypatch):
    argumentos = {}
    monkeypatch.setattr(connection.psycopg2, "connect", lambda **kw: argumentos.update(kw))
    monkeypatch.setenv("DB_CONNECT_TIMEOUT", "5s")

    connection.get_connection()
    assert argumentos["connect_timeout"] == 5


# --- Corte con la base caída ---

class Reloj:
    def __init__(self):
        self.ahora = 1000.0

    def monotonic(self):
        return self.ahora


@pytest.fixture
def base_caida(monkeypatch):
    reloj = Reloj()
    intentos = []

    def conectar():
        intentos.append(reloj.ahora)
        raise psycopg2.OperationalError("connection timeout expired")

    monkeypatch.setattr(uso_service.reloj, "monotonic", reloj.monotonic)
    monkeypatch.setattr(uso_service, "get_connection", conectar)
    return reloj, intentos


def test_corte_saltea_registros_y_luego_reintenta(base_caida, capsys):
    reloj, intentos = base_caida

    uso_service.registrar_evento("detalle_fondo", None)
    assert intentos == [1000.0]
    assert uso_service.en_pausa()

    # Durante la pausa no se intenta conectar
    for segundos in (1, 15, uso_service.SEGUNDOS_PAUSA - 0.1):
        reloj.ahora = 1000.0 + segundos
        uso_service.registrar_evento("detalle_fondo", None)
    assert intentos == [1000.0]

    # Pasada la pausa, reintenta (y como sigue caída, vuelve a pausar)
    reloj.ahora = 1000.0 + uso_service.SEGUNDOS_PAUSA
    uso_service.registrar_evento("detalle_fondo", None)
    assert intentos == [1000.0, 1000.0 + uso_service.SEGUNDOS_PAUSA]
    assert uso_service.en_pausa()

    # Un aviso por corte, no por evento
    assert capsys.readouterr().out.count("[USO] Sin conexión") == 2


def test_corte_avisa_una_vez_si_fallan_varios_a_la_vez(base_caida, capsys):
    uso_service._pausar(psycopg2.OperationalError("caída"))
    uso_service._pausar(psycopg2.OperationalError("caída"))
    assert capsys.readouterr().out.count("[USO] Sin conexión") == 1


def test_corte_vuelve_a_registrar_cuando_la_base_vuelve(base_caida, monkeypatch):
    reloj, _ = base_caida
    uso_service.registrar_evento("detalle_fondo", None)

    insertados = []

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, sql, params):
            insertados.append(params)

    class Conexion:
        def cursor(self):
            return Cursor()

        def commit(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(uso_service, "get_connection", lambda: Conexion())
    reloj.ahora += uso_service.SEGUNDOS_PAUSA
    uso_service.registrar_evento("detalle_fondo", "u1")

    assert insertados == [("detalle_fondo", "u1")]
    assert not uso_service.en_pausa()


def test_otros_errores_no_activan_el_corte(monkeypatch):
    def falla():
        raise RuntimeError("otro error")

    monkeypatch.setattr(uso_service, "get_connection", falla)
    uso_service.registrar_evento("detalle_fondo", None)
    assert not uso_service.en_pausa()


def test_get_connection_tiene_connect_timeout(monkeypatch):
    argumentos = {}
    monkeypatch.setattr(connection.psycopg2, "connect", lambda **kw: argumentos.update(kw))

    monkeypatch.delenv("DB_CONNECT_TIMEOUT", raising=False)
    connection.get_connection()
    assert argumentos["connect_timeout"] == 5

    monkeypatch.setenv("DB_CONNECT_TIMEOUT", "2")
    connection.get_connection()
    assert argumentos["connect_timeout"] == 2


def test_registrar_evento_nunca_lanza(monkeypatch):
    def sin_base():
        raise RuntimeError("sin base")

    monkeypatch.setattr(uso_service, "get_connection", sin_base)
    assert uso_service.registrar_evento("detalle_fondo", None) is None


# --- Endpoint ---

def _cliente_admin(usuario):
    app_admin = FastAPI()
    app_admin.include_router(uso.router_admin)
    app_admin.dependency_overrides[obtener_usuario_actual] = lambda: usuario
    return TestClient(app_admin)


@pytest.fixture
def resumen(monkeypatch):
    llamadas = []

    def falso(desde, hasta):
        llamadas.append((desde, hasta))
        return {"desde": desde.isoformat(), "hasta": hasta.isoformat()}

    monkeypatch.setattr(uso_service, "resumen_uso", falso)
    monkeypatch.setattr(uso, "hoy_uruguay", lambda: date(2026, 10, 26))
    return llamadas


def test_uso_sin_token_401(resumen):
    app_sin_token = FastAPI()
    app_sin_token.include_router(uso.router_admin)
    response = TestClient(app_sin_token).get("/api/admin/analisis/uso")

    assert response.status_code == 401
    assert resumen == []


def test_uso_sin_rol_admin_403(resumen):
    response = _cliente_admin(USUARIO).get("/api/admin/analisis/uso")
    assert response.status_code == 403
    assert resumen == []


def test_uso_con_rol_admin_por_defecto_ultimos_30_dias(resumen):
    response = _cliente_admin(ADMIN).get("/api/admin/analisis/uso")

    assert response.status_code == 200
    assert resumen == [(date(2026, 9, 26), date(2026, 10, 26))]


def test_uso_con_periodo(resumen):
    response = _cliente_admin(ADMIN).get(
        "/api/admin/analisis/uso", params={"desde": "2026-01-01", "hasta": "2026-01-31"}
    )

    assert response.status_code == 200
    assert response.json() == {"desde": "2026-01-01", "hasta": "2026-01-31"}


@pytest.mark.parametrize(
    "params",
    [
        {"desde": "2026-13-01"},
        {"hasta": "ayer"},
        {"desde": "2026-02-01", "hasta": "2026-01-01"},
    ],
)
def test_uso_periodo_invalido(resumen, params):
    response = _cliente_admin(ADMIN).get("/api/admin/analisis/uso", params=params)

    assert response.status_code == 400
    assert response.json()["detail"] == "El período es inválido."
    assert resumen == []


def test_uso_periodo_mayor_a_366_dias(resumen):
    response = _cliente_admin(ADMIN).get(
        "/api/admin/analisis/uso", params={"desde": "2025-01-01", "hasta": "2026-01-03"}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "El período no puede superar 366 días."


def test_uso_periodo_de_366_dias_es_valido(resumen):
    response = _cliente_admin(ADMIN).get(
        "/api/admin/analisis/uso", params={"desde": "2024-01-01", "hasta": "2025-01-01"}
    )
    assert response.status_code == 200


# --- resumen_uso con base falsa ---

class CursorFalso:
    def __init__(self, tablas, respuestas):
        self.tablas = tablas
        self.respuestas = respuestas
        self.consultas = []
        self._resultado = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self.consultas.append((sql, params))
        if "to_regclass" in sql:
            nombre = params[0].removeprefix("public.")
            self._resultado = [(nombre if nombre in self.tablas else None,)]
            return
        for fragmento, filas in self.respuestas.items():
            if fragmento in sql:
                self._resultado = filas
                return
        raise AssertionError(f"Consulta inesperada: {sql}")

    def fetchone(self):
        return self._resultado[0]

    def fetchall(self):
        return self._resultado


class ConexionFalsa:
    def __init__(self, cursor):
        self._cursor = cursor
        self.cerrada = False

    def cursor(self):
        return self._cursor

    def close(self):
        self.cerrada = True


def _con_base(monkeypatch, tablas, respuestas=None):
    cursor = CursorFalso(tablas, respuestas or {})
    conexion = ConexionFalsa(cursor)
    monkeypatch.setattr(uso_service, "get_connection", lambda: conexion)
    return cursor, conexion


def test_resumen_uso_rellena_todos_los_dias(monkeypatch):
    cursor, conexion = _con_base(
        monkeypatch,
        {"evento_uso", "usuarios"},
        {
            "COUNT(DISTINCT usuario_sub)": [(7, 2)],
            "GROUP BY tipo": [("busqueda_repositorio", 4), ("detalle_fondo", 3)],
            "GROUP BY dia": [(date(2026, 10, 2), 5), (date(2026, 10, 4), 2)],
            "GROUP BY estado": [("aprobado", 3), ("pendiente", 1)],
            "TRIM(perfil)": [("Investigador", 2), (None, 2)],
        },
    )

    datos = uso_service.resumen_uso(date(2026, 10, 1), date(2026, 10, 5))

    assert conexion.cerrada
    assert datos["total_eventos"] == 7
    assert datos["usuarios_distintos"] == 2
    assert datos["busquedas"] == 4
    assert datos["por_funcionalidad"] == [
        {"clave": "busqueda_repositorio", "etiqueta": "Búsquedas en el repositorio", "cantidad": 4},
        {"clave": "detalle_fondo", "etiqueta": "Detalle de fondos", "cantidad": 3},
    ]
    assert datos["por_dia"] == [
        {"periodo": "2026-10-01", "cantidad": 0},
        {"periodo": "2026-10-02", "cantidad": 5},
        {"periodo": "2026-10-03", "cantidad": 0},
        {"periodo": "2026-10-04", "cantidad": 2},
        {"periodo": "2026-10-05", "cantidad": 0},
    ]
    assert datos["usuarios_registrados"] == {
        "total": 4,
        "por_estado": [
            {"etiqueta": "Pendiente", "cantidad": 1},
            {"etiqueta": "Aprobado", "cantidad": 3},
            {"etiqueta": "Rechazado", "cantidad": 0},
        ],
        "por_perfil": [
            {"etiqueta": "Investigador", "cantidad": 2},
            {"etiqueta": "Sin dato", "cantidad": 2},
        ],
    }

    # El rango es inclusivo en días de Uruguay: desde 00:00-03 hasta el día siguiente 00:00-03
    _, params = next(c for c in cursor.consultas if "COUNT(DISTINCT" in c[0])
    inicio, fin = params
    assert inicio.isoformat() == "2026-10-01T00:00:00-03:00"
    assert fin.isoformat() == "2026-10-06T00:00:00-03:00"


def test_resumen_uso_sin_tablas_devuelve_ceros(monkeypatch):
    _, conexion = _con_base(monkeypatch, set())

    datos = uso_service.resumen_uso(date(2026, 10, 1), date(2026, 10, 3))

    assert conexion.cerrada
    assert datos["total_eventos"] == 0
    assert datos["usuarios_distintos"] == 0
    assert datos["busquedas"] == 0
    assert datos["por_funcionalidad"] == []
    assert [d["cantidad"] for d in datos["por_dia"]] == [0, 0, 0]
    assert datos["usuarios_registrados"]["total"] == 0
    assert datos["usuarios_registrados"]["por_perfil"] == []
