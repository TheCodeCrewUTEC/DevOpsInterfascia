from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import obtener_usuario_actual
from app.routers import alertas
from app.services import alerta_service

USUARIO = {"sub": "usuario-1", "email": "ana@example.com"}

app = FastAPI()
app.include_router(alertas.router)
app.dependency_overrides[obtener_usuario_actual] = lambda: USUARIO

client = TestClient(app)

# Sin override: obtener_usuario_actual de verdad, que exige token
app_sin_token = FastAPI()
app_sin_token.include_router(alertas.router)
client_sin_token = TestClient(app_sin_token)

AHORA = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)

PREFERENCIAS_VALIDAS = {
    "alerta_apertura": True,
    "alerta_cierre": True,
    "alerta_actualizacion": False,
    "dias_anticipacion_cierre": 7,
    "email_habilitado": False,
}


class ServicioFalso:
    """Reemplaza las funciones de alerta_service y registra con qué se llamaron."""

    def __init__(self):
        self.llamadas = []
        self.convocatorias = {10}
        self.suscripciones = {}
        self.ajenas = {99}
        self.preferencias = dict(alerta_service.PREFERENCIAS_POR_DEFECTO)

    def _registrar(self, nombre, *args):
        self.llamadas.append((nombre, args))

    def existe_convocatoria(self, id):
        return id in self.convocatorias

    def crear_suscripcion(self, usuario_sub, tipo, convocatoria_id, valor):
        self._registrar("crear_suscripcion", usuario_sub, tipo, convocatoria_id, valor)
        clave = (usuario_sub, tipo, convocatoria_id, (valor or "").lower())
        creada = clave not in self.suscripciones
        if creada:
            self.suscripciones[clave] = {
                "id": len(self.suscripciones) + 1,
                "tipo": tipo,
                "convocatoria_id": convocatoria_id,
                "valor": valor,
                "titulo_convocatoria": None,
                "creado": AHORA,
            }
        return self.suscripciones[clave], creada

    def eliminar_suscripcion(self, usuario_sub, id):
        self._registrar("eliminar_suscripcion", usuario_sub, id)
        return id not in self.ajenas and any(s["id"] == id for s in self.suscripciones.values())

    def obtener_preferencias(self, usuario_sub):
        self._registrar("obtener_preferencias", usuario_sub)
        return dict(self.preferencias)

    def guardar_preferencias(self, usuario_sub, datos, email):
        self._registrar("guardar_preferencias", usuario_sub, datos, email)
        self.preferencias.update(datos, email=email or self.preferencias.get("email"))
        return dict(self.preferencias)

    def listar_notificaciones(self, usuario_sub, solo_no_leidas, tipo, page, limit):
        self._registrar("listar_notificaciones", usuario_sub, solo_no_leidas, tipo, page, limit)
        return {"items": [], "page": page, "limit": limit, "total": 0, "total_pages": 0, "no_leidas": 0}

    def obtener_notificacion(self, usuario_sub, id):
        self._registrar("obtener_notificacion", usuario_sub, id)
        return None

    def eliminar_leidas(self, usuario_sub):
        self._registrar("eliminar_leidas", usuario_sub)
        return 3

    def instituciones_disponibles(self):
        return ["ANII", "UTEC"]


@pytest.fixture
def servicio(monkeypatch):
    falso = ServicioFalso()
    for nombre in (
        "existe_convocatoria", "crear_suscripcion", "eliminar_suscripcion",
        "obtener_preferencias", "guardar_preferencias", "listar_notificaciones",
        "obtener_notificacion", "eliminar_leidas", "instituciones_disponibles",
    ):
        monkeypatch.setattr(alerta_service, nombre, getattr(falso, nombre))
    return falso


@pytest.mark.parametrize(
    "metodo, ruta",
    [
        ("get", "/api/alertas/suscripciones"),
        ("get", "/api/alertas/preferencias"),
        ("get", "/api/alertas/notificaciones"),
        ("post", "/api/alertas/notificaciones/marcar-leidas"),
    ],
)
def test_sin_token_responde_401(servicio, metodo, ruta):
    response = getattr(client_sin_token, metodo)(ruta)

    assert response.status_code == 401
    assert servicio.llamadas == []


def test_opciones_es_publico(servicio):
    response = client_sin_token.get("/api/alertas/opciones")

    assert response.status_code == 200
    assert response.json() == {
        "tipos_alerta": ["apertura", "cierre", "actualizacion"],
        "tematicas": list(alerta_service.TEMATICAS),
        "instituciones": ["ANII", "UTEC"],
    }


def test_suscripcion_a_convocatoria_inexistente(servicio):
    response = client.post("/api/alertas/suscripciones", json={"tipo": "convocatoria", "convocatoria_id": 5})

    assert response.status_code == 404
    assert servicio.llamadas == []


def test_suscripcion_a_convocatoria_sin_id(servicio):
    response = client.post("/api/alertas/suscripciones", json={"tipo": "convocatoria"})

    assert response.status_code == 400


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"tipo": "tematica", "valor": "Astrología"},
        {"tipo": "tematica"},
        {"tipo": "institucion", "valor": "   "},
    ],
)
def test_suscripcion_invalida(servicio, cuerpo):
    response = client.post("/api/alertas/suscripciones", json=cuerpo)

    assert response.status_code == 400
    assert servicio.llamadas == []


def test_suscripcion_nueva_201_y_repetida_200(servicio):
    primera = client.post("/api/alertas/suscripciones", json={"tipo": "tematica", "valor": "salud"})
    repetida = client.post("/api/alertas/suscripciones", json={"tipo": "tematica", "valor": "Salud"})

    assert primera.status_code == 201
    assert repetida.status_code == 200
    assert primera.json()["id"] == repetida.json()["id"]
    # La temática se guarda como figura en la lista y con el usuario del token
    assert servicio.llamadas[0] == ("crear_suscripcion", ("usuario-1", "tematica", None, "Salud"))


def test_suscripcion_institucion_demasiado_larga(servicio):
    response = client.post("/api/alertas/suscripciones", json={"tipo": "institucion", "valor": "A" * 201})

    assert response.status_code == 400
    assert "200 caracteres" in response.json()["detail"]
    assert servicio.llamadas == []


def test_suscripcion_institucion_de_200_caracteres_se_acepta(servicio):
    response = client.post(
        "/api/alertas/suscripciones", json={"tipo": "institucion", "valor": "  " + "A" * 200 + "  "}
    )

    assert response.status_code == 201
    assert servicio.llamadas[0] == ("crear_suscripcion", ("usuario-1", "institucion", None, "A" * 200))


def test_suscripcion_a_convocatoria_ignora_valor(servicio):
    response = client.post(
        "/api/alertas/suscripciones",
        json={"tipo": "convocatoria", "convocatoria_id": 10, "valor": "algo"},
    )

    assert response.status_code == 201
    assert servicio.llamadas[0] == ("crear_suscripcion", ("usuario-1", "convocatoria", 10, None))


def test_eliminar_suscripcion_ajena(servicio):
    response = client.delete("/api/alertas/suscripciones/99")

    assert response.status_code == 404
    assert servicio.llamadas == [("eliminar_suscripcion", ("usuario-1", 99))]


@pytest.mark.parametrize("dias", [0, 61])
def test_preferencias_dias_fuera_de_rango(servicio, dias):
    response = client.put(
        "/api/alertas/preferencias",
        json={**PREFERENCIAS_VALIDAS, "dias_anticipacion_cierre": dias},
    )

    assert response.status_code == 422


def test_preferencias_email_sin_correo(servicio):
    app.dependency_overrides[obtener_usuario_actual] = lambda: {"sub": "usuario-1"}
    try:
        response = client.put(
            "/api/alertas/preferencias",
            json={**PREFERENCIAS_VALIDAS, "email_habilitado": True},
        )
    finally:
        app.dependency_overrides[obtener_usuario_actual] = lambda: USUARIO

    assert response.status_code == 400
    assert response.json()["detail"] == "No hay un correo válido asociado a tu cuenta."
    assert not any(nombre == "guardar_preferencias" for nombre, _ in servicio.llamadas)


def test_preferencias_guarda_el_correo_del_token(servicio):
    response = client.put(
        "/api/alertas/preferencias",
        json={**PREFERENCIAS_VALIDAS, "email_habilitado": True},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "ana@example.com"
    nombre, args = servicio.llamadas[-1]
    assert nombre == "guardar_preferencias"
    assert args[0] == "usuario-1"
    assert args[2] == "ana@example.com"


def test_ver_preferencias_completa_el_correo_del_token(servicio):
    response = client.get("/api/alertas/preferencias")

    assert response.status_code == 200
    assert response.json()["email"] == "ana@example.com"
    assert response.json()["dias_anticipacion_cierre"] == 7


def test_notificaciones_tipo_invalido(servicio):
    response = client.get("/api/alertas/notificaciones", params={"tipo": "otro"})

    assert response.status_code == 400
    assert servicio.llamadas == []


def test_notificaciones_pasa_el_usuario_al_servicio(servicio):
    response = client.get(
        "/api/alertas/notificaciones",
        params={"tipo": "cierre", "solo_no_leidas": "true", "page": 2, "limit": 5},
    )

    assert response.status_code == 200
    assert servicio.llamadas == [("listar_notificaciones", ("usuario-1", True, "cierre", 2, 5))]


def test_notificaciones_limit_maximo(servicio):
    response = client.get("/api/alertas/notificaciones", params={"limit": 101})

    assert response.status_code == 422


def test_notificacion_ajena(servicio):
    response = client.get("/api/alertas/notificaciones/7")

    assert response.status_code == 404
    assert servicio.llamadas == [("obtener_notificacion", ("usuario-1", 7))]


def test_eliminar_notificaciones_sin_solo_leidas(servicio):
    response = client.delete("/api/alertas/notificaciones")

    assert response.status_code == 400
    assert servicio.llamadas == []


def test_eliminar_notificaciones_leidas(servicio):
    response = client.delete("/api/alertas/notificaciones", params={"solo_leidas": "true"})

    assert response.status_code == 200
    assert response.json() == {"eliminadas": 3}
    assert servicio.llamadas == [("eliminar_leidas", ("usuario-1",))]


# --- Servicio con una conexión falsa ---

class CursorFalso:
    def __init__(self, filas):
        self.filas = list(filas)
        self.ejecutadas = []
        self.description = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, parametros=None):
        self.ejecutadas.append((sql, parametros))
        if "preferencia_notificacion" in sql:
            self.description = [(c.strip(),) for c in alerta_service.COLUMNAS_PREFERENCIAS.split(",")]

    def fetchone(self):
        return self.filas.pop(0) if self.filas else None


class ConexionFalsa:
    def __init__(self, cursor):
        self._cursor = cursor
        self.cerrada = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self._cursor

    def close(self):
        self.cerrada = True


def test_obtener_preferencias_por_defecto_sin_insertar(monkeypatch):
    cursor = CursorFalso([])
    conexion = ConexionFalsa(cursor)
    monkeypatch.setattr(alerta_service, "get_connection", lambda: conexion)

    preferencias = alerta_service.obtener_preferencias("usuario-1")

    assert preferencias == alerta_service.PREFERENCIAS_POR_DEFECTO
    assert len(cursor.ejecutadas) == 1
    assert cursor.ejecutadas[0][0].lstrip().startswith("SELECT")
    assert conexion.cerrada


def test_guardar_preferencias_upsert(monkeypatch):
    fila = (True, False, True, 15, True, AHORA, "ana@example.com")
    cursor = CursorFalso([fila])
    conexion = ConexionFalsa(cursor)
    monkeypatch.setattr(alerta_service, "get_connection", lambda: conexion)

    guardado = alerta_service.guardar_preferencias(
        "usuario-1",
        {**PREFERENCIAS_VALIDAS, "dias_anticipacion_cierre": 15, "email_habilitado": True},
        "  ana@example.com ",
    )

    sql, parametros = cursor.ejecutadas[0]
    assert "ON CONFLICT (usuario_sub) DO UPDATE" in sql
    assert "WHEN NOT EXCLUDED.email_habilitado THEN NULL" in sql
    assert parametros[0] == "usuario-1"
    assert parametros[-1] == "ana@example.com"
    assert guardado["dias_anticipacion_cierre"] == 15
    assert guardado["email_habilitado_desde"] == AHORA
    assert conexion.cerrada


# --- Administración ---

def _cliente_admin(usuario):
    app_admin = FastAPI()
    app_admin.include_router(alertas.router_admin)
    app_admin.dependency_overrides[obtener_usuario_actual] = lambda: usuario
    return TestClient(app_admin)


@pytest.fixture
def deteccion(monkeypatch):
    from app.services import deteccion_alertas_service

    llamadas = []

    def falsa(nombre, resultado):
        def funcion(*args, **kwargs):
            llamadas.append(nombre)
            return resultado
        return funcion

    monkeypatch.setattr(deteccion_alertas_service, "revisar_convocatorias", falsa("revisar", {"inicial": False, "aperturas": 1, "actualizaciones": 0, "nuevas": 1}))
    monkeypatch.setattr(deteccion_alertas_service, "avisar_cierres", falsa("cierres", {"cierres": 2}))
    monkeypatch.setattr(deteccion_alertas_service, "enviar_correos_pendientes", falsa("correos", {"omitido": "smtp no configurado"}))
    return llamadas


def test_revisar_alertas_sin_rol_admin_403(deteccion):
    response = _cliente_admin(USUARIO).post("/api/admin/alertas/revisar")

    assert response.status_code == 403
    assert deteccion == []


def test_revisar_alertas_con_rol_admin(deteccion):
    admin = {**USUARIO, "realm_access": {"roles": ["admin"]}}
    response = _cliente_admin(admin).post("/api/admin/alertas/revisar")

    assert response.status_code == 200
    assert response.json() == {
        "revision": {"inicial": False, "aperturas": 1, "actualizaciones": 0, "nuevas": 1},
        "cierres": {"cierres": 2},
        "correos": {"omitido": "smtp no configurado"},
    }
    assert deteccion == ["revisar", "cierres", "correos"]
