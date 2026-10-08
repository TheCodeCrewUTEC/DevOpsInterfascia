import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import obtener_usuario_actual
from app.routers import perfil
from app.services import keycloak_admin_service as keycloak

app = FastAPI()
app.include_router(perfil.router)
app.dependency_overrides[obtener_usuario_actual] = lambda: {"sub": "usuario-1"}

client = TestClient(app)

PERFIL_VALIDO = {
    "nombre": "Ana",
    "apellido": "Pérez",
    "celular": "099 123 456",
    "departamento_residencia": "Rocha",
    "departamentos_actuacion": ["Rocha", "Maldonado"],
    "instituciones": ["UTEC"],
    "perfil_otro": None,
}


class KeycloakFalso:
    def __init__(self, contrasena="Actual#Segura123"):
        self.contrasena = contrasena
        self.bloqueo = {"disabled": False, "numFailures": 0, "lastFailure": 0, "failedLoginNotBefore": 0}
        self.cambios = []
        self.sesiones_cerradas = False

    def obtener_usuario(self, keycloak_id):
        return {
            "id": keycloak_id,
            "username": "ana@example.com",
            "email": "ana@example.com",
            "attributes": {"perfil": ["Investigador/a"]},
        }

    def verificar_contrasena(self, usuario, contrasena):
        return contrasena == self.contrasena

    def cambiar_contrasena(self, keycloak_id, contrasena):
        self.cambios.append(contrasena)

    def cerrar_sesiones(self, keycloak_id):
        self.sesiones_cerradas = True

    def estado_bloqueo(self, keycloak_id):
        return self.bloqueo


@pytest.fixture
def kc(monkeypatch):
    falso = KeycloakFalso()
    for nombre in (
        "obtener_usuario", "verificar_contrasena", "cambiar_contrasena", "cerrar_sesiones", "estado_bloqueo"
    ):
        monkeypatch.setattr(keycloak, nombre, getattr(falso, nombre))
    return falso


@pytest.mark.parametrize(
    "nueva",
    ["Corta#1A", "SoloLetrasLargas", "sinmayusculas1234", "SINMINUSCULAS123"],
)
def test_contrasena_que_no_cumple_la_politica(kc, nueva):
    response = client.post("/api/perfil/contrasena", json={"actual": kc.contrasena, "nueva": nueva})

    assert response.status_code == 400
    assert kc.cambios == []


@pytest.mark.parametrize(
    "nueva",
    ["SinNumeros#Largos", "sinmayuscula#123", "SinEspecial12345"],
)
def test_contrasena_con_tres_de_cuatro_categorias(kc, nueva):
    response = client.post("/api/perfil/contrasena", json={"actual": kc.contrasena, "nueva": nueva})

    assert response.status_code == 200
    assert kc.cambios == [nueva]


def test_contrasena_actual_incorrecta(kc):
    response = client.post(
        "/api/perfil/contrasena",
        json={"actual": "otra", "nueva": "Nueva#Segura456"},
    )

    assert response.status_code == 400
    assert response.json()["detail"].startswith("La contraseña actual no es correcta. Te quedan 4 intentos")
    assert kc.cambios == []


def test_ultimo_intento_y_bloqueo(kc):
    kc.bloqueo.update(numFailures=3, lastFailure=time.time() * 1000)
    response = client.post("/api/perfil/contrasena", json={"actual": "otra", "nueva": "Nueva#Segura456"})
    assert "Te queda 1 intento" in response.json()["detail"]

    kc.bloqueo.update(numFailures=4)
    response = client.post("/api/perfil/contrasena", json={"actual": "otra", "nueva": "Nueva#Segura456"})
    assert response.json()["detail"].startswith("Usuario bloqueado por intentos fallidos")


def test_cuenta_bloqueada_no_prueba_la_contrasena(kc):
    kc.bloqueo.update(disabled=True, failedLoginNotBefore=time.time() + 600)
    response = client.post(
        "/api/perfil/contrasena",
        json={"actual": kc.contrasena, "nueva": "Nueva#Segura456"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Usuario bloqueado por intentos fallidos. Podés volver a intentar en 10 minutos."
    )
    assert kc.cambios == []


def test_cambio_de_contrasena_cierra_las_sesiones(kc):
    response = client.post(
        "/api/perfil/contrasena",
        json={"actual": kc.contrasena, "nueva": "Nueva#Segura456"},
    )

    assert response.status_code == 200
    assert kc.cambios == ["Nueva#Segura456"]
    assert kc.sesiones_cerradas


@pytest.mark.parametrize(
    "cambio",
    [
        {"celular": "abc"},
        {"departamento_residencia": "Buenos Aires"},
        {"departamentos_actuacion": []},
        {"instituciones": ["Otra cosa"]},
        {"nombre": "  "},
    ],
)
def test_perfil_invalido(kc, cambio):
    response = client.put("/api/perfil", json={**PERFIL_VALIDO, **cambio})

    assert response.status_code == 400
