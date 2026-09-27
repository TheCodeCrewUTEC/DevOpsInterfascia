from app.schemas.convocatoria import ConvocatoriaResponse
from pydantic import BaseModel


class ConvocatoriaPaginadaResponse(BaseModel):
    items: list[ConvocatoriaResponse]
    page: int
    limit: int
    total: int
    total_pages: int