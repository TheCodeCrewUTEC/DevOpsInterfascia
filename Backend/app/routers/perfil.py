import math
import os
import re
import time

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


# Misma protección de fuerza bruta del realm (failureFactor, waitIncrementSeconds, maxDeltaTimeSeconds).
# La cuenta de servicio no puede leer la configuración del realm, por eso se repite acá.
INTENTOS_PERMITIDOS = int(os.getenv("KEYCLOAK_INTENTOS_PERMITIDOS", "5"))
MINUTOS_BLOQUEO = int(os.getenv("KEYCLOAK_MINUTOS_BLOQUEO", "15"))
HORAS_OLVIDO_FALLAS = 12


def _minutos(cantidad: int) -> str:
    return "1 minuto" if cantidad == 1 else f"{cantidad} minutos"


def _mensaje_bloqueado(minutos: int) -> str:
    return f"Usuario bloqueado por intentos fallidos. Podés volver a intentar en {_minutos(minutos)}."


def _fallas_vigentes(estado: dict) -> int:
    # Como Keycloak: si la última falla es muy vieja, la próxima empieza de cero
    ultima = estado.get("lastFailure") or 0
    if ultima and time.time() * 1000 - ultima > HORAS_OLVIDO_FALLAS * 3600 * 1000:
        return 0
    return estado.get("numFailures") or 0


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

        # Keycloak suma la falla en segundo plano: se lee el estado antes de probar
        bloqueo = keycloak.estado_bloqueo(usuario["sub"])
        if bloqueo.get("disabled"):
            segundos = (bloqueo.get("failedLoginNotBefore") or 0) - time.time()
            raise _invalido(_mensaje_bloqueado(max(1, math.ceil(segundos / 60))))

        if not keycloak.verificar_contrasena(datos["username"], cambio.actual):
            restantes = INTENTOS_PERMITIDOS - (_fallas_vigentes(bloqueo) + 1)
            if restantes <= 0:
                raise _invalido(_mensaje_bloqueado(MINUTOS_BLOQUEO))
            intentos = "Te queda 1 intento" if restantes == 1 else f"Te quedan {restantes} intentos"
            raise _invalido(
                f"La contraseña actual no es correcta. {intentos} antes de que la cuenta "
                f"se bloquee por {_minutos(MINUTOS_BLOQUEO)}."
            )

        keycloak.cambiar_contrasena(usuario["sub"], cambio.nueva)
        # Cierra todas las sesiones: hay que volver a entrar con la contraseña nueva
        keycloak.cerrar_sesiones(usuario["sub"])
    except keycloak.ContrasenaRechazada:
        raise _invalido("Keycloak rechazó la contraseña nueva: no cumple la política de contraseñas.")
    except keycloak.KeycloakAdminError as error:
        raise _error_keycloak(error)

    return {"ok": True}
