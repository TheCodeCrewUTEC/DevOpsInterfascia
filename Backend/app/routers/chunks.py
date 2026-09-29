from fastapi import APIRouter, HTTPException
from app.schemas.chunk import ChunkResponse
from app.services import chunk_service

router = APIRouter(
    prefix="/api/chunks",
    tags=["Chunks"]
)

@router.get("/", response_model=list[ChunkResponse])
def obtener_chunks():
    return chunk_service.obtener_chunks

@router.get("/{id}", response_model=ChunkResponse)
def obtener_chunk(id: int):
    chunk = chunk_service.obtener_chunk(id)
    
    if chunk is None:
        raise HTTPException(
            status_code=404,
            detail="Chunk no encontrada"
        )

    return chunk

