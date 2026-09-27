from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel

class ChunkResponse(BaseModel):
    id: int
    documento_id: int
    contenido: Optional[str] = None
    pagina: Optional[int] = None
    creado: Optional[datetime] = None