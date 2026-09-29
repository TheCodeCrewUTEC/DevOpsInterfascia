from app.schemas.convocatoria import ConvocatoriaResponse
from app.schemas.documento import DocumentoResponse


class ConvocatoriaDetalleResponse(ConvocatoriaResponse):
    documentos: list[DocumentoResponse] = []