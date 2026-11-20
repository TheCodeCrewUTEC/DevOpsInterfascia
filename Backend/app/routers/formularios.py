import hmac
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
    HTTPException
)
from pydantic import BaseModel

from app.auth import (
    ROLES_CONSULTOR,
    es_admin,
    obtener_usuario_opcional,
    requiere_algun_rol,
    tiene_algun_rol,
)
from app.services.respuesta_service_db import actualizar_respuestas
from app.services.dato_validado_service import (
    clave_campo,
    confirmar_job,
    datos_del_usuario,
)

from app.schemas.formulario_job import FormularioJobResponse

from app.services.formulario_ande_service import (
    campos_para_consultor,
    listar_formularios_abiertos,
    metadatos_del_job,
    opcion_mas_parecida,
)
from app.services.formulario_job_service import (
    actualizar_estado_job,
    crear_job,
    listar_jobs_usuario,
)

from app.services.file_service import (
    nombre_disponible,
    sanitizar_nombre_archivo,
    validar_extension
)

from app.database.connection import get_connection

from app.services.queue_service import encolar_formulario, sacar_formulario_de_la_cola

router = APIRouter(
    prefix="/formularios",
    tags=["Formularios"]
)

STORAGE_PATH = Path("storage/formularios")
LIMITE_DOCUMENTOS = 3


class CambioRespuesta(BaseModel):
    id: int
    respuesta: str | None = None


def token_de_consulta_valido(recibido: str | None, guardado: str | None) -> bool:
    if not recibido or not guardado:
        return False
    try:
        return hmac.compare_digest(recibido, guardado)
    except (TypeError, ValueError):
        return False


def verificar_acceso_job(
    cur,
    job_id: int,
    usuario: dict | None,
    consulta_token: str | None = None,
):
    """Devuelve (id, estado) del job si el usuario puede verlo.

    Un job con dueño solo lo ven su dueño, los admin y quien tenga el token
    que devolvió el alta. Los jobs viejos (sin dueño) siguen visibles como antes.
    Se responde 404 para no revelar jobs ajenos.
    """

    cur.execute(
        """
        SELECT id, estado, usuario_sub, consulta_token
        FROM formulario_job
        WHERE id = %s
        """,
        (job_id,)
    )

    job = cur.fetchone()

    if job:
        dueno = job[2]
        if (
            token_de_consulta_valido(consulta_token, job[3])
            or dueno is None
            or es_admin(usuario)
            or (usuario and usuario.get("sub") == dueno)
        ):
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
    formulario: UploadFile | None = File(None),
    formulario_id: int | None = Form(None),
    documentos: list[UploadFile] = File(
        ...,
        media_type="multipart/form-data"
    ),
    usuario: dict = Depends(requiere_algun_rol(*ROLES_CONSULTOR)),
):

    tiene_archivo = formulario is not None and bool(formulario.filename)
    if tiene_archivo and formulario_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Elegí un formulario de ANDE o un PDF, no los dos",
        )
    if not tiene_archivo and formulario_id is None:
        raise HTTPException(
            status_code=400,
            detail="Seleccioná un formulario de ANDE o subí un PDF",
        )

    # VALIDAR FORMULARIO
    if tiene_archivo and not validar_extension(formulario.filename):
        raise HTTPException(
            status_code=400,
            detail="Formato de formulario no permitido"
        )

    if formulario_id is not None and not campos_para_consultor(formulario_id):
        raise HTTPException(
            status_code=404,
            detail="No está ese formulario de ANDE",
        )

    if not documentos:
        raise HTTPException(
            status_code=400,
            detail="Debe enviar al menos un documento"
        )

    if len(documentos) > LIMITE_DOCUMENTOS:
        raise HTTPException(
            status_code=400,
            detail="Podés adjuntar hasta 3 documentos del proyecto"
        )

    # CREAR JOB
    job = crear_job(None, usuario.get("sub"), formulario_id)

    job_id = job["id"]

    # CREAR CARPETA DEL JOB
    carpeta_job = STORAGE_PATH / f"job_{job_id}"

    carpeta_job.mkdir(
        parents=True,
        exist_ok=True
    )

    # GUARDAR FORMULARIO
    if tiene_archivo:
        nombre_formulario = nombre_disponible(
            carpeta_job,
            sanitizar_nombre_archivo(formulario.filename),
        )

        formulario_path = carpeta_job / nombre_formulario

        with formulario_path.open("wb") as buffer:

            while contenido := await formulario.read(
                1024 * 1024
            ):
                buffer.write(contenido)

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

        # Sanitizar nombre y evitar pisar el formulario u otro documento
        nombre_documento = nombre_disponible(
            carpeta_job,
            sanitizar_nombre_archivo(documento.filename),
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
        "creado": job["creado"],
        "consulta_token": job["consulta_token"],
    }
        

@router.get("/convocatorias-abiertas")
def listar_convocatorias_abiertas(
    _usuario: dict = Depends(requiere_algun_rol(*ROLES_CONSULTOR)),
):
    return listar_formularios_abiertos()


@router.get("/jobs")
def listar_formularios(
    usuario: dict = Depends(requiere_algun_rol(*ROLES_CONSULTOR)),
):
    sub = usuario.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="No se pudo identificar al usuario")
    return listar_jobs_usuario(sub)


@router.post("/jobs/{job_id}/cancelar")
async def cancelar_formulario_job(
    job_id: int,
    consulta: str | None = None,
    usuario: dict | None = Depends(obtener_usuario_opcional),
):
    """Corta la generación: saca el job de la cola y el worker no lo retoma."""

    if usuario is not None and not tiene_algun_rol(usuario, ROLES_CONSULTOR):
        if not consulta:
            raise HTTPException(
                status_code=403,
                detail="No tenés permisos para esta acción",
            )
        usuario = None

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            _, estado = verificar_acceso_job(cur, job_id, usuario, consulta)
    finally:
        conn.close()

    if estado == "CANCELLED":
        await sacar_formulario_de_la_cola(job_id)
        return {"id": job_id, "estado": "CANCELLED"}

    if estado not in ("PENDING", "PROCESSING"):
        raise HTTPException(
            status_code=409,
            detail="Ese formulario ya terminó",
        )

    actualizar_estado_job(job_id, "CANCELLED")
    await sacar_formulario_de_la_cola(job_id)

    return {"id": job_id, "estado": "CANCELLED"}


@router.get("/jobs/{job_id}/resultado")
def obtener_resultado_job(
    job_id: int,
    consulta: str | None = None,
    usuario: dict | None = Depends(obtener_usuario_opcional),
):
    # Sin rol de consultor solo se puede seguir un trabajo con su token de consulta.
    if usuario is not None and not tiene_algun_rol(usuario, ROLES_CONSULTOR):
        if not consulta:
            raise HTTPException(
                status_code=403,
                detail="No tenés permisos para esta acción",
            )
        usuario = None

    conn = get_connection()

    try:

        with conn.cursor() as cur:

            job_id_db, estado = verificar_acceso_job(cur, job_id, usuario, consulta)

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

            cur.execute(
                "SELECT validado_en FROM formulario_job WHERE id = %s",
                (job_id,)
            )
            validado_en = cur.fetchone()[0]

            # Lo que el usuario confirmó en formularios anteriores se ofrece
            # como sugerencia; nunca reemplaza solo la respuesta de la IA.
            guardados = (
                datos_del_usuario(cur, usuario["sub"])
                if usuario and usuario.get("sub")
                else {}
            )

            colas: dict[str, list] = {}
            for meta in metadatos_del_job(job_id_db):
                colas.setdefault(meta["etiqueta"], []).append(meta)

            respuestas = []
            por_selector: dict[str, str] = {}

            for (
                respuesta_id, campo, respuesta, fuentes,
                tipo, pagina, respuesta_ia, editada,
            ) in filas:

                cola = colas.get(campo) or []
                meta = cola.pop(0) if cola else {}
                mapa = meta.get("opciones_por_valor") or {}
                depende_de = meta.get("depende_de")
                columnas = meta.get("columnas") or []
                if columnas:
                    opciones = []
                elif depende_de and mapa:
                    opciones = list(mapa.get(por_selector.get(depende_de) or "") or [])
                else:
                    opciones = list(meta.get("opciones") or [])
                if opciones and not editada:
                    elegida = opcion_mas_parecida(respuesta, opciones)
                    if elegida:
                        respuesta = elegida
                    elegida_ia = opcion_mas_parecida(respuesta_ia, opciones)
                    if elegida_ia:
                        respuesta_ia = elegida_ia

                selector = meta.get("selector")
                if selector:
                    por_selector[selector] = respuesta or ""

                dato_guardado = guardados.get(clave_campo(campo))
                if dato_guardado == (respuesta or "").strip():
                    dato_guardado = None

                respuestas.append({
                    "id": respuesta_id,
                    "campo": campo,
                    "respuesta": respuesta,
                    "fuentes": fuentes or [],
                    "tipo": tipo,
                    "pagina": pagina,
                    "respuesta_ia": respuesta_ia,
                    "editada": editada,
                    "dato_guardado": dato_guardado,
                    "opciones": opciones,
                    "selector": selector,
                    "depende_de": depende_de,
                    "opciones_por_valor": mapa if depende_de else {},
                    "columnas": columnas,
                })

            return {
                "job_id": job_id_db,
                "estado": estado,
                "total_respuestas": len(respuestas),
                "validado": validado_en is not None,
                "respuestas": respuestas
            }

    finally:
        conn.close()


@router.put("/jobs/{job_id}/respuestas")
def guardar_correcciones(
    job_id: int,
    cambios: list[CambioRespuesta],
    usuario: dict = Depends(requiere_algun_rol(*ROLES_CONSULTOR)),
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


@router.post("/jobs/{job_id}/confirmar")
def confirmar_formulario(
    job_id: int,
    usuario: dict = Depends(requiere_algun_rol(*ROLES_CONSULTOR)),
):
    """La persona revisó el formulario y confirma sus datos (human in the loop).

    Las respuestas no vacías quedan guardadas como datos validados del proyecto
    y se sugieren al completar el próximo formulario.
    """

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            _, estado = verificar_acceso_job(cur, job_id, usuario)
    finally:
        conn.close()

    if estado != "COMPLETED":
        raise HTTPException(
            status_code=409,
            detail="El formulario todavía no está completo"
        )

    guardados = confirmar_job(job_id, usuario["sub"])

    return {"guardados": guardados}
