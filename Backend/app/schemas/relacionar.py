from typing import Optional

from pydantic import BaseModel, field_validator


class RelacionarRequest(BaseModel):
    descripcion: str

    @field_validator("descripcion")
    @classmethod
    def validar_descripcion(cls, valor: str) -> str:
        texto = valor.strip()
        if len(texto) < 20:
            raise ValueError("Contame un poco más del proyecto.")
        if len(texto) > 12000:
            raise ValueError("El texto puede tener hasta 12000 caracteres.")
        return texto


class FondoRecomendado(BaseModel):
    id: int
    titulo: Optional[str] = None
    institucion: Optional[str] = None
    estado: Optional[str] = None
    fecha_apertura: Optional[str] = None
    fecha_cierre: Optional[str] = None
    descripcion: Optional[str] = None
    financiamiento: Optional[str] = None
    motivo: str


class InvestigadorRecomendado(BaseModel):
    id: int
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    institucion: Optional[str] = None
    titulo: Optional[str] = None
    investigaciones: Optional[str] = None
    nivel_sni: Optional[str] = None
    categoria_sni: Optional[str] = None
    motivo: str


class ProyectoRecomendado(BaseModel):
    nombre: str
    anio: Optional[str] = None
    descripcion: Optional[str] = None
    investigador_id: Optional[int] = None
    investigador: Optional[str] = None
    motivo: str


class RelacionarResponse(BaseModel):
    resumen: str
    fondos: list[FondoRecomendado]
    investigadores: list[InvestigadorRecomendado]
    proyectos: list[ProyectoRecomendado]


class FondoCitado(BaseModel):
    id: int
    titulo: Optional[str] = None
    estado: Optional[str] = None
    motivo: Optional[str] = None


class MensajeRelacionar(BaseModel):
    rol: str
    contenido: str
    fondos: list[FondoCitado] = []


class ConversacionRelacionar(BaseModel):
    id: int
    estado: str
    error: Optional[str] = None
    documentos: list[str]
    mensajes: list[MensajeRelacionar]


class RespuestaRelacionar(BaseModel):
    contenido: str
    fondos: list[FondoCitado]


class PreguntaRelacionar(BaseModel):
    texto: str

    @field_validator("texto")
    @classmethod
    def validar_texto(cls, valor: str) -> str:
        texto = valor.strip()
        if len(texto) < 2:
            raise ValueError("Escribí la pregunta.")
        if len(texto) > 2000:
            raise ValueError("La pregunta puede tener hasta 2000 caracteres.")
        return texto
