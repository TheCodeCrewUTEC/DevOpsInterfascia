from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
    HTTPException
)
from pydantic import BaseModel

from app.auth import (
    es_admin,
    obtener_usuario_actual,
    obtener_usuario_opcional,
)
from app.services.respuesta_service_db import actualizar_respuestas

from app.schemas.formulario_job import FormularioJobResponse

from app.services.formulario_job_service import crear_job

from app.services.file_service import (
    sanitizar_nombre_archivo,
    validar_extension
)

from app.database.connection import get_connection

from app.services.queue_service import encolar_formulario

router = APIRouter(
    prefix="/formularios",
    tags=["Formularios"]
)

STORAGE_PATH = Path("storage/formularios")


class CambioRespuesta(BaseModel):
    id: int
    respuesta: str | None = None


def verificar_acceso_job(cur, job_id: int, usuario: dict | None):
    """Devuelve (id, estado) del job si el usuario puede verlo.

    Un job con dueño solo lo ven su dueño y los admin. Los jobs viejos (sin dueño)
    siguen visibles como antes. Se responde 404 para no revelar jobs ajenos.
    """

    cur.execute(
        """
        SELECT id, estado, usuario_sub
        FROM formulario_job
        WHERE id = %s
        """,
        (job_id,)
    )

    job = cur.fetchone()

    if job:
        dueno = job[2]
        if dueno is None or es_admin(usuario) or (usuario and usuario.get("sub") == dueno):
            return job[0], job[1]

    raise HTTPException(
        status_code=404,
        detail=f"No existe el Job {job_id}"
    )


@router.post(
    "/jobs",
    response_model=FormularioJobResponse
)
async def crear_formulario_job(
    formulario: UploadFile = File(...),
    documentos: list[UploadFile] = File(
        ...,
        media_type="multipart/form-data"
    ),
    usuario: dict | None = Depends(obtener_usuario_opcional),
):

    # VALIDAR FORMULARIO
    if not formulario.filename:
        raise HTTPException(
            status_code=400,
            detail="El archivo no tiene nombre"
        )

    if not validar_extension(formulario.filename):
        raise HTTPException(
            status_code=400,
            detail="Formato de formulario no permitido"
        )

    # CREAR JOB
    job = crear_job(None, usuario.get("sub") if usuario else None)

    job_id = job["id"]

    # CREAR CARPETA DEL JOB
    carpeta_job = STORAGE_PATH / f"job_{job_id}"

    carpeta_job.mkdir(
        parents=True,
        exist_ok=True
    )

    # GUARDAR FORMULARIO
    nombre_formulario = sanitizar_nombre_archivo(
        formulario.filename
    )

    formulario_path = carpeta_job / nombre_formulario

    with formulario_path.open("wb") as buffer:

        while contenido := await formulario.read(
            1024 * 1024
        ):
            buffer.write(contenido)

    # GUARDAR RUTA DEL FORMULARIO
    conn = get_connection()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                UPDATE formulario_job
                SET formulario_path = %s
                WHERE id = %s
                """,
                (
                    str(formulario_path),
                    job_id
                )
            )

        conn.commit()

    finally:
        conn.close()

    # VALIDAR Y GUARDAR DOCUMENTOS
    if not documentos:

        raise HTTPException(
            status_code=400,
            detail="Debe enviar al menos un documento"
        )

    archivos_guardados = []

    for documento in documentos:

        # Validar nombre
        if not documento.filename:

            raise HTTPException(
                status_code=400,
                detail="Uno de los documentos no tiene nombre"
            )

        # Validar extensión
        if not validar_extension(
            documento.filename
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Formato de documento no permitido: "
                    f"{documento.filename}"
                )
            )

        # Sanitizar nombre
        nombre_documento = sanitizar_nombre_archivo(
            documento.filename
        )

        # Crear ruta
        documento_path = carpeta_job / nombre_documento

        # Guardar documento
        with documento_path.open("wb") as buffer:

            while contenido := await documento.read(
                1024 * 1024
            ):
                buffer.write(contenido)


        archivos_guardados.append(
            {
                "nombre": nombre_documento,
                "ruta": str(documento_path)
            }
        )

    # ENCOLAR JOB EN REDIS
    await encolar_formulario(job_id)

    return {
        "id": job["id"],
        "estado": job["estado"],
        "creado": job["creado"]
    }
        

@router.get("/jobs/{job_id}/resultado")
def obtener_resultado_job(
    job_id: int,
    usuario: dict | None = Depends(obtener_usuario_opcional),
):

    conn = get_connection()

    try:

        with conn.cursor() as cur:

            job_id_db, estado = verificar_acceso_job(cur, job_id, usuario)

            cur.execute(
                """
                SELECT
                    id,
                    campo,
                    respuesta,
                    fuentes,
                    tipo,
                    pagina,
                    respuesta_ia,
                    editada
                FROM respuesta_formulario
                WHERE job_id = %s
                ORDER BY id
                """,
                (job_id,)
            )

            filas = cur.fetchall()

            respuestas = []

            for (
                respuesta_id, campo, respuesta, fuentes,
                tipo, pagina, respuesta_ia, editada,
            ) in filas:

                respuestas.append({
                    "id": respuesta_id,
                    "campo": campo,
                    "respuesta": respuesta,
                    "fuentes": fuentes or [],
                    "tipo": tipo,
                    "pagina": pagina,
                    "respuesta_ia": respuesta_ia,
                    "editada": editada,
                })

            return {
                "job_id": job_id_db,
                "estado": estado,
                "total_respuestas": len(respuestas),
                "respuestas": respuestas
            }

    finally:
        conn.close()


@router.put("/jobs/{job_id}/respuestas")
def guardar_correcciones(
    job_id: int,
    cambios: list[CambioRespuesta],
    usuario: dict = Depends(obtener_usuario_actual),
):
    """Guarda lo que el usuario corrigió en el formulario completado."""

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            verificar_acceso_job(cur, job_id, usuario)
    finally:
        conn.close()

    actualizados = actualizar_respuestas(
        job_id,
        [cambio.model_dump() for cambio in cambios]
    )

    return {"actualizados": actualizados}
