from datetime import datetime
from pydantic import BaseModel

class FormularioJobResponse(BaseModel):
    id: int
    estado: str
    creado: datetime
    consulta_token: str