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


@pytest.fixture
def kc(monkeypatch):
    falso = KeycloakFalso()
    for nombre in ("obtener_usuario", "verificar_contrasena", "cambiar_contrasena", "cerrar_sesiones"):
        monkeypatch.setattr(keycloak, nombre, getattr(falso, nombre))
    return falso


@pytest.mark.parametrize(
    "nueva",
    ["Corta#1A", "SinNumeros#Largos", "sinmayuscula#123", "SinEspecial12345"],
)
def test_contrasena_que_no_cumple_la_politica(kc, nueva):
    response = client.post("/api/perfil/contrasena", json={"actual": kc.contrasena, "nueva": nueva})

    assert response.status_code == 400
    assert kc.cambios == []


def test_contrasena_actual_incorrecta(kc):
    response = client.post(
        "/api/perfil/contrasena",
        json={"actual": "otra", "nueva": "Nueva#Segura456"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "La contraseña actual no es correcta."
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
