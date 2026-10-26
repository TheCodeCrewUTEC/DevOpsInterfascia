import re

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.auth import obtener_usuario_actual, requiere_rol
from app.schemas.alerta import (
    CambioLeida,
    NotificacionesPaginadas,
    NotificacionResponse,
    Preferencias,
    PreferenciasResponse,
    SuscripcionNueva,
    SuscripcionResponse,
)
from app.services import alerta_service, deteccion_alertas_service

# Rutas del usuario. Las de administración van en un router_admin aparte en este
# mismo archivo, para poder protegerlas con requiere_rol("admin") de una sola vez.
router = APIRouter(prefix="/api/alertas", tags=["Alertas"])
router_admin = APIRouter(
    prefix="/api/admin/alertas",
    tags=["Alertas"],
    dependencies=[Depends(requiere_rol("admin"))],
)

PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LARGO_MAXIMO_INSTITUCION = 200


def _invalido(detalle: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detalle)


def _no_encontrada(detalle: str) -> HTTPException:
    return HTTPException(status_code=404, detail=detalle)


def _email_valido(email: str | None) -> str | None:
    email = (email or "").strip()
    return email if PATRON_EMAIL.match(email) else None


@router.get("/opciones")
def opciones():
    return {
        "tipos_alerta": list(alerta_service.TIPOS_ALERTA),
        "tematicas": list(alerta_service.TEMATICAS),
        "instituciones": alerta_service.instituciones_disponibles(),
    }


# --- Suscripciones ---

@router.get("/suscripciones", response_model=list[SuscripcionResponse])
def listar_suscripciones(usuario: dict = Depends(obtener_usuario_actual)):
    return alerta_service.listar_suscripciones(usuario["sub"])


@router.post("/suscripciones", response_model=SuscripcionResponse, status_code=201)
def crear_suscripcion(
    nueva: SuscripcionNueva,
    response: Response,
    usuario: dict = Depends(obtener_usuario_actual),
):
    convocatoria_id = None
    valor = None

    if nueva.tipo == "convocatoria":
        if nueva.convocatoria_id is None:
            raise _invalido("Elegí la convocatoria a seguir.")
        if not alerta_service.existe_convocatoria(nueva.convocatoria_id):
            raise _no_encontrada("Convocatoria no encontrada")
        convocatoria_id = nueva.convocatoria_id

    elif nueva.tipo == "tematica":
        # Se guarda tal cual figura en la lista, aunque llegue con otras mayúsculas
        elegida = (nueva.valor or "").strip().lower()
        valor = next((t for t in alerta_service.TEMATICAS if t.lower() == elegida), None)
        if valor is None:
            raise _invalido("Elegí una temática válida.")

    else:
        valor = " ".join((nueva.valor or "").split())
        if not valor:
            raise _invalido("Indicá la institución a seguir.")
        # Se valida acá y no con max_length en el schema para responder 400 con un
        # mensaje legible (el 422 de Pydantic trae una lista que el front no muestra)
        if len(valor) > LARGO_MAXIMO_INSTITUCION:
            raise _invalido(
                f"El nombre de la institución no puede superar {LARGO_MAXIMO_INSTITUCION} caracteres."
            )

    suscripcion, creada = alerta_service.crear_suscripcion(
        usuario["sub"], nueva.tipo, convocatoria_id, valor
    )
    # 201 si es nueva; 200 si ya estaba suscripto (no es un error)
    response.status_code = 201 if creada else 200
    return suscripcion


@router.delete("/suscripciones/{id}", status_code=204)
def eliminar_suscripcion(id: int, usuario: dict = Depends(obtener_usuario_actual)):
    if not alerta_service.eliminar_suscripcion(usuario["sub"], id):
        raise _no_encontrada("Suscripción no encontrada")


# --- Preferencias ---

@router.get("/preferencias", response_model=PreferenciasResponse)
def ver_preferencias(usuario: dict = Depends(obtener_usuario_actual)):
    preferencias = alerta_service.obtener_preferencias(usuario["sub"])

    if not preferencias.get("email"):
        preferencias["email"] = _email_valido(usuario.get("email"))

    return preferencias


@router.put("/preferencias", response_model=PreferenciasResponse)
def guardar_preferencias(
    cambio: Preferencias,
    usuario: dict = Depends(obtener_usuario_actual),
):
    email = _email_valido(usuario.get("email"))

    if cambio.email_habilitado and email is None:
        guardado = alerta_service.obtener_preferencias(usuario["sub"]).get("email")
        if _email_valido(guardado) is None:
            raise _invalido("No hay un correo válido asociado a tu cuenta.")

    return alerta_service.guardar_preferencias(usuario["sub"], cambio.model_dump(), email)


# --- Notificaciones (rutas fijas antes que las de {id}) ---

@router.get("/notificaciones", response_model=NotificacionesPaginadas)
def listar_notificaciones(
    solo_no_leidas: bool = False,
    tipo: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    usuario: dict = Depends(obtener_usuario_actual),
):
    tipo = (tipo or "").strip() or None

    if tipo is not None and tipo not in alerta_service.TIPOS_ALERTA:
        raise _invalido("Tipo de alerta inválido.")

    return alerta_service.listar_notificaciones(
        usuario["sub"],
        solo_no_leidas=solo_no_leidas,
        tipo=tipo,
        page=page,
        limit=limit,
    )


@router.post("/notificaciones/marcar-leidas")
def marcar_todas_leidas(usuario: dict = Depends(obtener_usuario_actual)):
    return {"actualizadas": alerta_service.marcar_todas_leidas(usuario["sub"])}


@router.delete("/notificaciones")
def eliminar_leidas(
    solo_leidas: bool = False,
    usuario: dict = Depends(obtener_usuario_actual),
):
    # Por ahora solo se permite vaciar las leídas; borrar todo de una no se ofrece
    if not solo_leidas:
        raise _invalido("Solo se pueden eliminar en conjunto las notificaciones leídas.")

    return {"eliminadas": alerta_service.eliminar_leidas(usuario["sub"])}


@router.get("/notificaciones/{id}", response_model=NotificacionResponse)
def ver_notificacion(id: int, usuario: dict = Depends(obtener_usuario_actual)):
    notificacion = alerta_service.obtener_notificacion(usuario["sub"], id)

    if notificacion is None:
        raise _no_encontrada("Notificación no encontrada")

    return notificacion


@router.patch("/notificaciones/{id}", response_model=NotificacionResponse)
def cambiar_leida(
    id: int,
    cambio: CambioLeida,
    usuario: dict = Depends(obtener_usuario_actual),
):
    notificacion = alerta_service.marcar_leida(usuario["sub"], id, cambio.leida)

    if notificacion is None:
        raise _no_encontrada("Notificación no encontrada")

    return notificacion


@router.delete("/notificaciones/{id}", status_code=204)
def eliminar_notificacion(id: int, usuario: dict = Depends(obtener_usuario_actual)):
    if not alerta_service.eliminar_notificacion(usuario["sub"], id):
        raise _no_encontrada("Notificación no encontrada")


# --- Administración ---

@router_admin.post("/revisar")
def revisar_ahora():
    """Corre a mano lo mismo que los cron del worker (útil para probar sin esperar)."""

    return {
        "revision": deteccion_alertas_service.revisar_convocatorias(),
        "cierres": deteccion_alertas_service.avisar_cierres(),
        "correos": deteccion_alertas_service.enviar_correos_pendientes(),
    }
