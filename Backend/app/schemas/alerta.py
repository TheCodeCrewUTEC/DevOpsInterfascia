from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class SuscripcionNueva(BaseModel):
    tipo: Literal["convocatoria", "institucion", "tematica"]
    convocatoria_id: Optional[int] = None
    valor: Optional[str] = None


class SuscripcionResponse(BaseModel):
    id: int
    tipo: str
    convocatoria_id: Optional[int] = None
    valor: Optional[str] = None
    titulo_convocatoria: Optional[str] = None
    creado: datetime


class Preferencias(BaseModel):
    alerta_apertura: bool
    alerta_cierre: bool
    alerta_actualizacion: bool
    dias_anticipacion_cierre: int = Field(ge=1, le=60)
    email_habilitado: bool


class PreferenciasResponse(Preferencias):
    email: Optional[str] = None


class NotificacionResponse(BaseModel):
    id: int
    tipo: str
    convocatoria_id: Optional[int] = None
    titulo: str
    mensaje: str
    detalle: dict | list | None = None
    leida: bool
    creado: datetime
    email_enviado_en: Optional[datetime] = None


class NotificacionesPaginadas(BaseModel):
    items: list[NotificacionResponse]
    page: int
    limit: int
    total: int
    total_pages: int
    no_leidas: int


class CambioLeida(BaseModel):
    leida: bool
