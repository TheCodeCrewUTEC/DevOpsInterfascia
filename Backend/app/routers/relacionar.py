from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.auth import obtener_usuario_actual
from app.schemas.relacionar import (
    ConversacionRelacionar,
    PreguntaRelacionar,
    RelacionarRequest,
    RelacionarResponse,
    RespuestaRelacionar,
)
from app.services.file_service import sanitizar_nombre_archivo, validar_extension
from app.services.queue_service import encolar_relacionar
from app.services.relacionar_chat_service import (
    carpeta_conversacion,
    crear_conversacion,
    marcar_error,
    obtener_conversacion,
    preparar_base,
    responder,
)
from app.services.relacionar_service import RelacionarError, recomendar

router = APIRouter(
    prefix="/api/relacionar",
    tags=["Relacionar"],
)

LIMITE_DOCUMENTOS = 3
LIMITE_BYTES = 20 * 1024 * 1024
EXTENSIONES = "PDF, Word, Excel o texto"


@router.post("", response_model=RelacionarResponse, include_in_schema=False)
@router.post("/", response_model=RelacionarResponse)
def relacionar_proyecto(
    pedido: RelacionarRequest,
    _usuario: dict = Depends(obtener_usuario_actual),
):
    try:
        return recomendar(pedido.descripcion)
    except RelacionarError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


def _usuario_sub(usuario: dict) -> str:
    sub = usuario.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Tenés que iniciar sesión.")
    return sub


def _nombres_documentos(documentos: list[UploadFile]) -> list[str]:
    if not documentos:
        raise HTTPException(status_code=400, detail="Subí al menos un documento del proyecto.")
    if len(documentos) > LIMITE_DOCUMENTOS:
        raise HTTPException(status_code=400, detail="Podés adjuntar hasta 3 documentos.")

    vistos = set()
    nombres = []
    for documento in documentos:
        if not documento.filename:
            raise HTTPException(status_code=400, detail="Uno de los documentos no tiene nombre.")
        if not validar_extension(documento.filename):
            raise HTTPException(
                status_code=400,
                detail=f"Formato no permitido ({EXTENSIONES}): {documento.filename}",
            )
        base = sanitizar_nombre_archivo(documento.filename)
        candidato = base
        indice = 2
        while candidato in vistos:
            ruta = Path(base)
            candidato = f"{ruta.stem}_{indice}{ruta.suffix}"
            indice += 1
        vistos.add(candidato)
        nombres.append(candidato)
    return nombres


async def _guardar_documento(destino: Path, archivo: UploadFile) -> None:
    total = 0
    with destino.open("wb") as buffer:
        while bloque := await archivo.read(1024 * 1024):
            total += len(bloque)
            if total > LIMITE_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail="Cada documento puede pesar hasta 20 MB.",
                )
            buffer.write(bloque)
    if total == 0:
        raise HTTPException(status_code=400, detail="Uno de los documentos está vacío.")


@router.post("/conversaciones", response_model=ConversacionRelacionar)
async def abrir_conversacion(
    documentos: list[UploadFile] = File(...),
    usuario: dict = Depends(obtener_usuario_actual),
):
    sub = _usuario_sub(usuario)
    nombres = _nombres_documentos(documentos)
    conversacion = crear_conversacion(sub, nombres)
    conversacion_id = conversacion["id"]
    carpeta = carpeta_conversacion(conversacion_id)
    carpeta.mkdir(parents=True, exist_ok=True)

    try:
        for nombre, archivo in zip(nombres, documentos):
            await _guardar_documento(carpeta / nombre, archivo)
        await encolar_relacionar(conversacion_id)
    except HTTPException:
        marcar_error(conversacion_id, "No se pudieron guardar los documentos.")
        raise
    except Exception as error:
        marcar_error(conversacion_id, "No se pudo empezar a leer los documentos.")
        raise HTTPException(
            status_code=503,
            detail="No se pudo empezar a leer los documentos.",
        ) from error

    preparar_base()
    return conversacion


@router.get("/conversaciones/{conversacion_id}", response_model=ConversacionRelacionar)
def ver_conversacion(
    conversacion_id: int,
    usuario: dict = Depends(obtener_usuario_actual),
):
    conversacion = obtener_conversacion(conversacion_id, _usuario_sub(usuario))
    if conversacion is None:
        raise HTTPException(status_code=404, detail="No encontré esa conversación.")
    return conversacion


@router.post("/conversaciones/{conversacion_id}/mensajes", response_model=RespuestaRelacionar)
def preguntar(
    conversacion_id: int,
    pedido: PreguntaRelacionar,
    usuario: dict = Depends(obtener_usuario_actual),
):
    try:
        respuesta = responder(conversacion_id, _usuario_sub(usuario), pedido.texto)
    except RelacionarError as error:
        codigo = 409 if "leyendo" in str(error) else 503
        raise HTTPException(status_code=codigo, detail=str(error)) from error
    if respuesta is None:
        raise HTTPException(status_code=404, detail="No encontré esa conversación.")
    return respuesta
