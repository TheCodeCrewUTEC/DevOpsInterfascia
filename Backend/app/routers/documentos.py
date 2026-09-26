from fastapi import APIRouter, HTTPException
from app.schemas.documento import DocumentoResponse
from app.schemas.chunk import ChunkResponse
from app.schemas.documento_detalle import DocumentoDetalleResponse
from app.services import documento_service, chunk_service

router = APIRouter(
    prefix="/api/documentos",
    tags=["Documentos"]
)

@router.get("/", response_model=list[DocumentoResponse])
def obtener_documentos():
    return documento_service.obtener_documentos()


@router.get("/{id}", response_model=DocumentoDetalleResponse)
def obtener_documento(id: int):

    documento = documento_service.obtener_documento(id)

    if documento is None:
        raise HTTPException(
            status_code=404,
            detail="Documento no encontrado"
        )

    return documento

@router.get("/{id}/chunks", response_model=list[ChunkResponse])
def obtener_chunks(id: int):

    chunk = chunk_service.obtener_chunks_por_documento(id)

    if chunk is None:
        raise HTTPException(
            status_code=404,
            detail="Convocatoria no encontrada"
        )

    return chunk