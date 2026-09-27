from fastapi import APIRouter, HTTPException, Query
from app.schemas.convocatoria import ConvocatoriaResponse
from app.schemas.documento import DocumentoResponse
from app.schemas.convocatoria_detalle import ConvocatoriaDetalleResponse
from app.services import convocatoria_service, documento_service
from app.schemas.convocatoria_paginacion import ConvocatoriaPaginadaResponse
from datetime import date

router = APIRouter(
    prefix="/api/convocatorias",
    tags=["Convocatorias"]
)

@router.get("/", response_model=ConvocatoriaPaginadaResponse)
def obtener_convocatorias(
    estado: str | None = None,
    institucion: str | None = None,
    buscar: str | None = None,
    fecha_apertura_desde: date | None = None,
    fecha_apertura_hasta: date | None = None,
    fecha_cierre_desde: date | None = None,
    fecha_cierre_hasta: date | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    return convocatoria_service.obtener_convocatorias(
        estado=estado,
        institucion=institucion,
        buscar=buscar,
        fecha_apertura_desde=fecha_apertura_desde,
        fecha_apertura_hasta=fecha_apertura_hasta,
        fecha_cierre_desde=fecha_cierre_desde,
        fecha_cierre_hasta=fecha_cierre_hasta,
        page=page,
        limit=limit
    )


@router.get("/{id}", response_model=ConvocatoriaDetalleResponse)
def obtener_convocatoria(id: int):

    convocatoria = convocatoria_service.obtener_convocatoria(id)

    if convocatoria is None:
        raise HTTPException(
            status_code=404,
            detail="Convocatoria no encontrada"
        )

    return convocatoria

@router.get("/{id}/documentos", response_model=list[DocumentoResponse])
def obtener_documentos(id: int):

    documentos = convocatoria_service.obtener_documento_por_convocatoria(id)

    if documentos is None:
        raise HTTPException(
            status_code=404,
            detail="Convocatoria no encontrada"
        )

    return documentos

