from fastapi import APIRouter, Depends
from app.auth import obtener_usuario_actual

router = APIRouter(
    prefix="/api/auth",
    tags=["Autenticación"]
)


@router.get("/me")
def obtener_usuario(usuario: dict = Depends(obtener_usuario_actual)):
    return {
        "id": usuario.get("sub"),
        "email": usuario.get("email"),
        "nombre": usuario.get("given_name"),
        "apellido": usuario.get("family_name"),
        "roles": usuario.get("realm_access", {}).get("roles", [])
    }
