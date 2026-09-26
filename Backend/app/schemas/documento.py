from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel

class DocumentoResponse(BaseModel):
    id: int
    convocatoria_id: int
    nombre: Optional[str] = None
    url: Optional[str] = None
    creado: Optional[datetime] = None