import os
from functools import lru_cache

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

load_dotenv()

# "iss" que Keycloak pone en los tokens (la URL pública del realm)
KEYCLOAK_ISSUER = os.getenv(
    "KEYCLOAK_ISSUER",
    "http://localhost:8080/realms/interfascia"
)

# Desde Docker, las claves públicas se descargan por la red interna
KEYCLOAK_INTERNAL_ISSUER = os.getenv("KEYCLOAK_INTERNAL_ISSUER", KEYCLOAK_ISSUER)

# Audiencia que agrega el mapper "audiencia-api" del cliente interfascia-frontend
KEYCLOAK_AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "interfascia-api")

bearer = HTTPBearer(auto_error=False)


@lru_cache
def obtener_jwks_client() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(
        f"{KEYCLOAK_INTERNAL_ISSUER}/protocol/openid-connect/certs"
    )


def _no_autorizado(detalle: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detalle,
        headers={"WWW-Authenticate": "Bearer"}
    )


def obtener_usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(bearer)
) -> dict:
    """Valida el access token de Keycloak y devuelve sus claims."""

    if credenciales is None:
        raise _no_autorizado("Falta el token de acceso")

    token = credenciales.credentials

    try:
        clave = obtener_jwks_client().get_signing_key_from_jwt(token)
    except jwt.PyJWKClientConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo contactar a Keycloak"
        )
    except (jwt.PyJWKClientError, jwt.InvalidTokenError):
        raise _no_autorizado("Token inválido")

    try:
        return jwt.decode(
            token,
            clave.key,
            algorithms=["RS256"],
            audience=KEYCLOAK_AUDIENCE,
            issuer=KEYCLOAK_ISSUER
        )
    except jwt.ExpiredSignatureError:
        raise _no_autorizado("Token vencido")
    except jwt.InvalidTokenError:
        raise _no_autorizado("Token inválido")


def obtener_usuario_opcional(
    credenciales: HTTPAuthorizationCredentials | None = Depends(bearer)
) -> dict | None:
    """Como obtener_usuario_actual, pero sin token devuelve None en vez de 401."""

    if credenciales is None:
        return None

    return obtener_usuario_actual(credenciales)


def es_admin(usuario: dict | None) -> bool:
    return bool(usuario) and "admin" in usuario.get("realm_access", {}).get("roles", [])


def requiere_rol(rol: str):
    """Dependencia que exige un rol de realm de Keycloak."""

    def verificar(usuario: dict = Depends(obtener_usuario_actual)) -> dict:
        roles = usuario.get("realm_access", {}).get("roles", [])

        if rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenés permisos para esta acción"
            )

        return usuario

    return verificar
