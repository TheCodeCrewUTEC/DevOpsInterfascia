from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ProyectoResponse(BaseModel):
    id: int
    nombre: Optional[str] = None
    estado: Optional[str] = None
    anio: Optional[str] = None
    descripcion: Optional[str] = None
    investigadores: Optional[str] = None
    creado: Optional[datetime] = None
