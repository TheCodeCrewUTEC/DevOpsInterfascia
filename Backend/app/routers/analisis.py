from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from app.auth import obtener_usuario_actual
from app.services import alerta_service, analisis_service
from app.services.analisis_service import FiltrosAnalisis
from app.services.deteccion_alertas_service import normalizar

# Análisis de datos (RF006). Solo lectura; cualquier usuario con sesión puede verlo.
router = APIRouter(
    prefix="/api/analisis",
    tags=["Análisis"],
    dependencies=[Depends(obtener_usuario_actual)],
)

LARGO_MAXIMO_ORGANISMO = 200


def _invalido(detalle: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detalle)


def _elegido(valor: str | None, opciones, error: str) -> str | None:
    """Devuelve la opción tal cual figura en la lista, aunque llegue con otras mayúsculas o sin tildes."""

    valor = (valor or "").strip()
    if not valor:
        return None

    elegido = next((o for o in opciones if normalizar(o) == normalizar(valor)), None)
    if elegido is None:
        raise _invalido(error)
    return elegido


def _fecha(valor: str | None) -> date | None:
    valor = (valor or "").strip()
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise _invalido("El período es inválido.")


# Fechas y opciones llegan como texto y se validan acá para responder 400 con un
# mensaje legible (el 422 de Pydantic trae una lista que el front no muestra)
def filtros(
    organismo: str | None = None,
    tematica: str | None = None,
    estado: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
) -> FiltrosAnalisis:
    organismo = " ".join((organismo or "").split()) or None
    if organismo and len(organismo) > LARGO_MAXIMO_ORGANISMO:
        raise _invalido(
            f"El organismo no puede superar {LARGO_MAXIMO_ORGANISMO} caracteres."
        )

    desde_fecha = _fecha(desde)
    hasta_fecha = _fecha(hasta)
    if desde_fecha and hasta_fecha and desde_fecha > hasta_fecha:
        raise _invalido("El período es inválido.")

    return FiltrosAnalisis(
        organismo=organismo,
        tematica=_elegido(tematica, alerta_service.TEMATICAS, "Elegí una temática válida."),
        estado=_elegido(estado, analisis_service.ESTADOS, "Elegí un estado válido."),
        desde=desde_fecha,
        hasta=hasta_fecha,
    )


@router.get("/opciones")
def opciones():
    return analisis_service.obtener_opciones()


@router.get("/resumen")
def resumen(f: FiltrosAnalisis = Depends(filtros)):
    return analisis_service.obtener_resumen(f)


@router.get("/fondos")
def fondos(f: FiltrosAnalisis = Depends(filtros)):
    return analisis_service.obtener_fondos(f)


@router.get("/investigadores")
def investigadores(f: FiltrosAnalisis = Depends(filtros)):
    return analisis_service.obtener_investigadores(f)


@router.get("/proyectos")
def proyectos(f: FiltrosAnalisis = Depends(filtros)):
    return analisis_service.obtener_proyectos(f)


@router.get("/tendencias")
def tendencias(agrupar: str = "anio", f: FiltrosAnalisis = Depends(filtros)):
    agrupar = (agrupar or "").strip().lower() or "anio"
    if agrupar not in analisis_service.AGRUPACIONES:
        raise _invalido("Agrupación inválida.")

    return analisis_service.obtener_tendencias(f, agrupar)
