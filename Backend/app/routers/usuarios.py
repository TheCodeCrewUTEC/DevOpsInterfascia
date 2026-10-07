import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel

from app.auth import requiere_rol
from app.services import keycloak_admin_service as keycloak
from app.services import usuario_service

# Secreto compartido con el listener de Keycloak (aviso de registro)
INTERNAL_API_SECRET = os.getenv("INTERNAL_API_SECRET", "")

router = APIRouter(tags=["Usuarios"])


class AvisoRegistro(BaseModel):
    keycloak_id: str


def _error_keycloak(error: keycloak.KeycloakAdminError) -> HTTPException:
    return HTTPException(status_code=502, detail=str(error))


@router.post("/internal/usuarios", include_in_schema=False)
def recibir_registro(
    aviso: AvisoRegistro,
    x_internal_secret: str = Header(default=""),
):
    if not INTERNAL_API_SECRET or not hmac.compare_digest(
        x_internal_secret, INTERNAL_API_SECRET
    ):
        raise HTTPException(status_code=401, detail="No autorizado")

    try:
        usuario = usuario_service.importar_desde_keycloak(aviso.keycloak_id)
    except keycloak.KeycloakAdminError as error:
        raise _error_keycloak(error)

    return {"keycloak_id": usuario["keycloak_id"], "estado": usuario["estado"]}


@router.get("/api/admin/usuarios")
def listar_usuarios(
    estado: str | None = Query(default=None),
    _admin: dict = Depends(requiere_rol("admin")),
):
    if estado is not None and estado not in usuario_service.ESTADOS:
        raise HTTPException(status_code=400, detail="Estado inválido")

    return usuario_service.listar_usuarios(estado)


def _revisar(keycloak_id: str, estado: str, admin: dict) -> dict:
    if estado != "aprobado" and keycloak_id == admin.get("sub"):
        raise HTTPException(
            status_code=400,
            detail="No podés deshabilitar tu propia cuenta",
        )

    try:
        # Keycloak primero: si falla, la tabla no queda diciendo algo que no pasó
        keycloak.cambiar_aprobacion(
            keycloak_id,
            habilitado=estado == "aprobado",
            estado=estado,
        )
        usuario_service.importar_desde_keycloak(keycloak_id)
    except keycloak.KeycloakAdminError as error:
        raise _error_keycloak(error)

    usuario = usuario_service.marcar_estado(
        keycloak_id,
        estado,
        admin.get("email") or admin.get("preferred_username"),
    )

    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return usuario


@router.post("/api/admin/usuarios/{keycloak_id}/aprobar")
def aprobar_usuario(
    keycloak_id: str,
    admin: dict = Depends(requiere_rol("admin")),
):
    return _revisar(keycloak_id, "aprobado", admin)


@router.post("/api/admin/usuarios/{keycloak_id}/rechazar")
def rechazar_usuario(
    keycloak_id: str,
    admin: dict = Depends(requiere_rol("admin")),
):
    return _revisar(keycloak_id, "rechazado", admin)


class CambioRol(BaseModel):
    rol: str | None = None


@router.put("/api/admin/usuarios/{keycloak_id}/rol")
def cambiar_rol(
    keycloak_id: str,
    cambio: CambioRol,
    admin: dict = Depends(requiere_rol("admin")),
):
    rol = cambio.rol or None

    if rol is not None and rol not in keycloak.ROLES_APP:
        raise HTTPException(status_code=400, detail="Rol inválido")

    if keycloak_id == admin.get("sub") and rol != "admin":
        raise HTTPException(
            status_code=400,
            detail="No podés quitarte el rol de administrador",
        )

    try:
        keycloak.cambiar_rol(keycloak_id, rol)
        return usuario_service.importar_desde_keycloak(keycloak_id)
    except keycloak.KeycloakAdminError as error:
        raise _error_keycloak(error)


@router.post("/api/admin/usuarios/sincronizar")
def sincronizar_usuarios(_admin: dict = Depends(requiere_rol("admin"))):
    try:
        total = usuario_service.sincronizar_desde_keycloak()
    except keycloak.KeycloakAdminError as error:
        raise _error_keycloak(error)

    return {"sincronizados": total}
