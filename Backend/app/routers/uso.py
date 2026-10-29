from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException

from app.auth import requiere_rol
from app.services import uso_service
from app.services.deteccion_alertas_service import hoy_uruguay

# Métricas de uso de la plataforma (RF006-08). Solo para administradores.
router_admin = APIRouter(
    prefix="/api/admin/analisis",
    tags=["Análisis"],
    dependencies=[Depends(requiere_rol("admin"))],
)

DIAS_POR_DEFECTO = 30
DIAS_MAXIMOS = 366


def _invalido(detalle: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detalle)


def _fecha(valor: str | None, por_defecto: date) -> date:
    valor = (valor or "").strip()
    if not valor:
        return por_defecto
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise _invalido("El período es inválido.")


@router_admin.get("/uso")
def uso(desde: str | None = None, hasta: str | None = None):
    # Llegan como texto para responder 400 con mensaje propio en vez del 422 de FastAPI
    hoy = hoy_uruguay()
    fecha_hasta = _fecha(hasta, hoy)
    fecha_desde = _fecha(desde, fecha_hasta - timedelta(days=DIAS_POR_DEFECTO))

    if fecha_desde > fecha_hasta:
        raise _invalido("El período es inválido.")
    if (fecha_hasta - fecha_desde).days > DIAS_MAXIMOS:
        raise _invalido("El período no puede superar 366 días.")

    return uso_service.resumen_uso(fecha_desde, fecha_hasta)
