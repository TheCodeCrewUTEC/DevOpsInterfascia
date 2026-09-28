import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app import auth

clave_privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class ClaveFalsa:
    key = clave_privada.public_key()


class JwksClientFalso:
    def get_signing_key_from_jwt(self, token):
        return ClaveFalsa()


app = FastAPI()


@app.get("/protegida")
def protegida(usuario: dict = Depends(auth.obtener_usuario_actual)):
    return {"email": usuario["email"]}


@app.get("/admin")
def admin(usuario: dict = Depends(auth.requiere_rol("admin"))):
    return {"ok": True}


client = TestClient(app)


@pytest.fixture(autouse=True)
def jwks_falso(monkeypatch):
    monkeypatch.setattr(auth, "obtener_jwks_client", lambda: JwksClientFalso())


def crear_token(**cambios):
    claims = {
        "iss": auth.KEYCLOAK_ISSUER,
        "aud": auth.KEYCLOAK_AUDIENCE,
        "sub": "123",
        "email": "test@interfascia.uy",
        "exp": int(time.time()) + 300,
        "realm_access": {"roles": []},
    }
    claims.update(cambios)
    return jwt.encode(claims, clave_privada, algorithm="RS256")


def pedir(ruta, token):
    return client.get(ruta, headers={"Authorization": f"Bearer {token}"})


def test_sin_token_devuelve_401():
    response = client.get("/protegida")

    assert response.status_code == 401


def test_token_valido():
    response = pedir("/protegida", crear_token())

    assert response.status_code == 200
    assert response.json() == {"email": "test@interfascia.uy"}


def test_token_vencido():
    response = pedir("/protegida", crear_token(exp=int(time.time()) - 10))

    assert response.status_code == 401
    assert response.json()["detail"] == "Token vencido"


def test_audiencia_incorrecta():
    response = pedir("/protegida", crear_token(aud="otra-api"))

    assert response.status_code == 401


def test_emisor_incorrecto():
    response = pedir("/protegida", crear_token(iss="http://otro-keycloak/realms/x"))

    assert response.status_code == 401


def test_rol_faltante_devuelve_403():
    response = pedir("/admin", crear_token())

    assert response.status_code == 403


def test_rol_presente():
    response = pedir("/admin", crear_token(realm_access={"roles": ["admin"]}))

    assert response.status_code == 200
