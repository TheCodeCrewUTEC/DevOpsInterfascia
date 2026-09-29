from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel

class ConvocatoriaResponse(BaseModel):
    id: int
    titulo: Optional[str] = None
    institucion: Optional[str] = None
    estado: Optional[str] = None
    fecha_apertura: Optional[date] = None
    fecha_cierre: Optional[date] = None
    descripcion: Optional[str] = None
    beneficiarios: Optional[str] = None
    requisitos: Optional[str] = None
    financiamiento: Optional[int] = None
    creado: Optional[datetime] = None