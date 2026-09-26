from app.schemas.documento import DocumentoResponse
from app.schemas.chunk import ChunkResponse

class DocumentoDetalleResponse(DocumentoResponse):
    chunks: list[ChunkResponse] = []