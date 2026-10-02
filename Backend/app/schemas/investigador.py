from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class InvestigadorResponse(BaseModel):
    id: int
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    institucion: Optional[str] = None
    titulo: Optional[str] = None
    investigaciones: Optional[str] = None
    nivel_sni: Optional[str] = None
    categoria_sni: Optional[str] = None
    creado: Optional[datetime] = None
