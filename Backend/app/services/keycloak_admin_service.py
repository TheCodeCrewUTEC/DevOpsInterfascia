import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

# Keycloak por la red interna de Docker (no por el dominio público)
KEYCLOAK_INTERNAL_ISSUER = os.getenv(
    "KEYCLOAK_INTERNAL_ISSUER",
    "http://localhost:8080/realms/interfascia"
).rstrip("/")

# Cliente con cuenta de servicio y permisos view-users / manage-users
CLIENT_ID = os.getenv("KEYCLOAK_BACKEND_CLIENT_ID", "interfascia-backend")
CLIENT_SECRET = os.getenv("KEYCLOAK_BACKEND_CLIENT_SECRET", "")

TOKEN_URL = f"{KEYCLOAK_INTERNAL_ISSUER}/protocol/openid-connect/token"
ADMIN_URL = KEYCLOAK_INTERNAL_ISSUER.replace("/realms/", "/admin/realms/", 1)

# Roles de realm que se asignan al registrarse (el resto son roles internos de Keycloak)
ROLES_APP = ("admin", "gestor_innovacion", "investigador", "emprendedor")

_token_cache: dict = {"valor": None, "vence": 0.0}


class KeycloakAdminError(Exception):
    pass


def _token() -> str:
    if _token_cache["valor"] and time.time() < _token_cache["vence"] - 30:
        return _token_cache["valor"]

    if not CLIENT_SECRET:
        raise KeycloakAdminError("Falta KEYCLOAK_BACKEND_CLIENT_SECRET")

    try:
        response = httpx.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
            timeout=10,
        )
    except httpx.HTTPError as error:
        raise KeycloakAdminError(f"No se pudo contactar a Keycloak: {error}")

    if response.status_code != 200:
        raise KeycloakAdminError(
            f"Keycloak rechazó el cliente {CLIENT_ID} ({response.status_code})"
        )

    datos = response.json()
    _token_cache["valor"] = datos["access_token"]
    _token_cache["vence"] = time.time() + datos.get("expires_in", 60)
    return _token_cache["valor"]


def _pedir(metodo: str, ruta: str, **kwargs) -> httpx.Response:
    try:
        response = httpx.request(
            metodo,
            f"{ADMIN_URL}{ruta}",
            headers={"Authorization": f"Bearer {_token()}"},
            timeout=15,
            **kwargs,
        )
    except httpx.HTTPError as error:
        raise KeycloakAdminError(f"No se pudo contactar a Keycloak: {error}")

    if response.status_code >= 400:
        raise KeycloakAdminError(
            f"Keycloak respondió {response.status_code} en {ruta}: {response.text[:200]}"
        )

    return response


def obtener_usuario(keycloak_id: str) -> dict:
    return _pedir("GET", f"/users/{keycloak_id}").json()


def listar_usuarios() -> list[dict]:
    usuarios = []
    inicio = 0
    tanda = 100

    while True:
        pagina = _pedir(
            "GET",
            "/users",
            params={"first": inicio, "max": tanda, "briefRepresentation": "false"},
        ).json()
        usuarios.extend(pagina)

        if len(pagina) < tanda:
            return usuarios

        inicio += tanda


def rol_de_usuario(keycloak_id: str) -> str | None:
    roles = _pedir("GET", f"/users/{keycloak_id}/role-mappings/realm").json()
    nombres = {rol["name"] for rol in roles}
    return next((rol for rol in ROLES_APP if rol in nombres), None)


def cambiar_rol(keycloak_id: str, rol: str | None) -> None:
    """Deja al usuario con un solo rol de la app (o ninguno, si rol es None)."""

    asignados = _pedir("GET", f"/users/{keycloak_id}/role-mappings/realm").json()
    sobrantes = [r for r in asignados if r["name"] in ROLES_APP and r["name"] != rol]

    if sobrantes:
        _pedir("DELETE", f"/users/{keycloak_id}/role-mappings/realm", json=sobrantes)

    if rol is None or any(r["name"] == rol for r in asignados):
        return

    # "available" solo pide manage-users (GET /roles/{nombre} pediría view-realm)
    disponibles = _pedir(
        "GET", f"/users/{keycloak_id}/role-mappings/realm/available"
    ).json()
    nuevo = next((r for r in disponibles if r["name"] == rol), None)

    if nuevo is None:
        raise KeycloakAdminError(f"El rol {rol} no existe en el realm")

    _pedir("POST", f"/users/{keycloak_id}/role-mappings/realm", json=[nuevo])


def cambiar_aprobacion(keycloak_id: str, habilitado: bool, estado: str) -> None:
    """Habilita o deshabilita la cuenta y deja el estado en el atributo estadoAprobacion."""

    # PUT reemplaza la representación: se manda la actual con los dos cambios
    usuario = obtener_usuario(keycloak_id)
    usuario["enabled"] = habilitado
    usuario.setdefault("attributes", {})["estadoAprobacion"] = [estado]

    _pedir("PUT", f"/users/{keycloak_id}", json=usuario)
