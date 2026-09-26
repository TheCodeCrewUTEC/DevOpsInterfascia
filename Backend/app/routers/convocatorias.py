from fastapi import APIRouter, HTTPException
from app.schemas.convocatoria import ConvocatoriaResponse
from app.schemas.documento import DocumentoResponse
from app.schemas.convocatoria_detalle import ConvocatoriaDetalleResponse
from app.services import convocatoria_service, documento_service

router = APIRouter(
    prefix="/api/convocatorias",
    tags=["Convocatorias"]
)

@router.get("/", response_model=list[ConvocatoriaResponse])
def obtener_convocatorias():
    return convocatoria_service.obtener_convocatorias()


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

