import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import obtener_usuario_actual
from app.services import keycloak_admin_service as keycloak
from app.services import usuario_service

router = APIRouter(tags=["Perfil"])

# Mismas opciones que el perfil de usuario del realm (Keycloak también las valida)
DEPARTAMENTOS = (
    "Artigas", "Canelones", "Cerro Largo", "Colonia", "Durazno", "Flores", "Florida",
    "Lavalleja", "Maldonado", "Montevideo", "Paysandú", "Río Negro", "Rivera", "Rocha",
    "Salto", "San José", "Soriano", "Tacuarembó", "Treinta y Tres",
)
INSTITUCIONES = ("UTEC", "UDELAR", "CURE", "UTU", "ANII", "Otra")
PATRON_CELULAR = re.compile(r"^\+?[0-9 ]{8,15}$")

# Misma passwordPolicy del realm: length(12) and digits(1) and upperCase(1) and specialChars(1)
REGLAS_CONTRASENA = (
    (lambda c: len(c) >= 12, "La contraseña debe tener al menos 12 caracteres."),
    (lambda c: any(ch.isdigit() for ch in c), "La contraseña debe incluir al menos un número."),
    (lambda c: any(ch.isupper() for ch in c), "La contraseña debe incluir al menos una letra mayúscula."),
    (
        lambda c: any(not ch.isalnum() for ch in c),
        "La contraseña debe incluir al menos un carácter especial (por ejemplo ! @ # $ %).",
    ),
)


class CambioPerfil(BaseModel):
    nombre: str
    apellido: str
    celular: str | None = None
    departamento_residencia: str
    departamentos_actuacion: list[str]
    instituciones: list[str]
    perfil_otro: str | None = None


class CambioContrasena(BaseModel):
    actual: str
    nueva: str


def _error_keycloak(error: keycloak.KeycloakAdminError) -> HTTPException:
    return HTTPException(status_code=502, detail=str(error))


def _invalido(detalle: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detalle)


def _sin_repetidos(valores: list[str]) -> list[str]:
    return list(dict.fromkeys(v.strip() for v in valores if v.strip()))


@router.get("/api/perfil")
def ver_perfil(usuario: dict = Depends(obtener_usuario_actual)):
    try:
        datos = keycloak.obtener_usuario(usuario["sub"])
        rol = keycloak.rol_de_usuario(usuario["sub"])
    except keycloak.KeycloakAdminError as error:
        raise _error_keycloak(error)

    perfil = usuario_service.datos_desde_keycloak(datos, rol)
    perfil.pop("estado", None)
    return perfil


@router.put("/api/perfil")
def actualizar_perfil(
    cambio: CambioPerfil,
    usuario: dict = Depends(obtener_usuario_actual),
):
    nombre = cambio.nombre.strip()
    apellido = cambio.apellido.strip()
    celular = (cambio.celular or "").strip()
    actuacion = _sin_repetidos(cambio.departamentos_actuacion)
    instituciones = _sin_repetidos(cambio.instituciones)

    if not nombre or not apellido:
        raise _invalido("El nombre y el apellido son obligatorios.")
    if celular and not PATRON_CELULAR.match(celular):
        raise _invalido("Ingresá un número de celular válido.")
    if cambio.departamento_residencia not in DEPARTAMENTOS:
        raise _invalido("Elegí un departamento de residencia válido.")
    if not actuacion or any(d not in DEPARTAMENTOS for d in actuacion):
        raise _invalido("Elegí al menos un departamento de actuación válido.")
    if not instituciones or any(i not in INSTITUCIONES for i in instituciones):
        raise _invalido("Elegí al menos una institución válida.")

    try:
        actual = keycloak.obtener_usuario(usuario["sub"])
        perfil = ((actual.get("attributes") or {}).get("perfil") or [None])[0]

        # El rol elegido no se cambia desde acá; solo el texto de "Otros"
        perfil_otro = (cambio.perfil_otro or "").strip() if perfil == "Otros" else ""
        if perfil == "Otros" and not perfil_otro:
            raise _invalido("Especificá tu rol.")

        actualizado = keycloak.actualizar_usuario(
            usuario["sub"],
            {"firstName": nombre, "lastName": apellido},
            {
                "celular": [celular] if celular else [],
                "departamentoResidencia": [cambio.departamento_residencia],
                "departamentosActuacion": actuacion,
                "instituciones": instituciones,
                "perfilOtro": [perfil_otro] if perfil_otro else [],
            },
        )
        guardado = usuario_service.importar_desde_keycloak(usuario["sub"], actualizado)
    except keycloak.KeycloakAdminError as error:
        raise _error_keycloak(error)

    guardado.pop("estado", None)
    return guardado


@router.post("/api/perfil/contrasena")
def cambiar_contrasena(
    cambio: CambioContrasena,
    usuario: dict = Depends(obtener_usuario_actual),
):
    for cumple, mensaje in REGLAS_CONTRASENA:
        if not cumple(cambio.nueva):
            raise _invalido(mensaje)

    if cambio.nueva == cambio.actual:
        raise _invalido("La contraseña nueva tiene que ser distinta de la actual.")

    try:
        datos = keycloak.obtener_usuario(usuario["sub"])

        for valor in (datos.get("username"), datos.get("email")):
            if valor and cambio.nueva.lower() == valor.lower():
                raise _invalido("La contraseña no puede ser igual a tu usuario ni a tu correo.")

        if not keycloak.verificar_contrasena(datos["username"], cambio.actual):
            raise _invalido("La contraseña actual no es correcta.")

        keycloak.cambiar_contrasena(usuario["sub"], cambio.nueva)
        # Cierra todas las sesiones: hay que volver a entrar con la contraseña nueva
        keycloak.cerrar_sesiones(usuario["sub"])
    except keycloak.ContrasenaRechazada:
        raise _invalido("Keycloak rechazó la contraseña nueva: no cumple la política de contraseñas.")
    except keycloak.KeycloakAdminError as error:
        raise _error_keycloak(error)

    return {"ok": True}
