import secrets
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.database.connection import get_connection

STORAGE_FORMULARIOS = Path("storage/formularios")
UMBRAL_EN_PROCESO = timedelta(minutes=5)

def crear_job(
    formulario_path: str | None,
    usuario_sub: str | None = None,
    formulario_ande_id: int | None = None,
):
    # La página que creó el job lo usa para consultarlo mientras Qwen trabaja,
    # aunque el access token de Keycloak (5 minutos) ya se haya vencido.
    consulta_token = secrets.token_urlsafe(32)

    conn = get_connection()

    try:
        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO formulario_job (
                    estado,
                    formulario_path,
                    usuario_sub,
                    consulta_token,
                    formulario_ande_id
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, estado, creado
                """,
                (
                    "PENDING",
                    formulario_path,
                    usuario_sub,
                    consulta_token,
                    formulario_ande_id,
                )
            )

            job = cur.fetchone()

        conn.commit()

        return {
            "id": job[0],
            "estado": job[1],
            "creado": job[2],
            "consulta_token": consulta_token,
        }

    finally:
        conn.close()

def listar_jobs_usuario(usuario_sub: str):
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT j.id, j.estado, j.creado, j.formulario_path, f.convocatoria
                FROM formulario_job j
                LEFT JOIN formularios f ON f.id = j.formulario_ande_id
                WHERE j.usuario_sub = %s
                ORDER BY j.creado DESC
                LIMIT 50
                """,
                (usuario_sub,),
            )
            filas = cur.fetchall()
    finally:
        conn.close()

    ahora = datetime.now(timezone.utc)
    formularios = []

    for job_id, estado, creado, formulario_path, convocatoria in filas:
        momento = creado if creado.tzinfo else creado.replace(tzinfo=timezone.utc)
        activo = estado in ("PENDING", "PROCESSING")
        formularios.append({
            "id": job_id,
            "estado": estado,
            "creado": creado,
            "nombre": Path(formulario_path).name if formulario_path else convocatoria,
            "en_proceso": activo and ahora - momento >= UMBRAL_EN_PROCESO,
        })

    return formularios


def obtener_job(job_id: int):
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    estado,
                    formulario_path,
                    creado,
                    iniciado,
                    finalizado,
                    resultado_path,
                    error,
                    formulario_ande_id
                FROM formulario_job
                WHERE id = %s
                """,
                (job_id,)
            )

            job = cur.fetchone()

        return job

    finally:
        conn.close()

def actualizar_estado_job(job_id: int, estado: str) -> bool:
    # CANCELLED no se pisa: si la persona cortó la generación, el worker no la
    # vuelve a marcar como PROCESSING, COMPLETED o FAILED.
    if estado == "CANCELLED":
        condicion = "estado IN ('PENDING', 'PROCESSING')"
    else:
        condicion = "estado IS DISTINCT FROM 'CANCELLED'"

    conn = get_connection()

    try:
        with conn.cursor() as cur:

            cur.execute(
                f"""
                UPDATE formulario_job
                SET estado = %s
                WHERE id = %s
                  AND {condicion}
                """,
                (
                    estado,
                    job_id
                )
            )
            actualizo = cur.rowcount > 0

        conn.commit()

    finally:
        conn.close()

    if actualizo and estado in ("COMPLETED", "FAILED", "CANCELLED"):
        eliminar_carpeta_job(job_id)

    return actualizo


def esta_cancelado(job_id: int) -> bool:
    job = obtener_job(job_id)
    return job is not None and job[1] == "CANCELLED"


def eliminar_carpeta_job(job_id: int):
    base = STORAGE_FORMULARIOS.resolve()
    carpeta = (STORAGE_FORMULARIOS / f"job_{job_id}").resolve()

    if carpeta != base and base not in carpeta.parents:
        return

    if not carpeta.is_dir():
        return

    try:
        shutil.rmtree(carpeta)
    except OSError as error:
        print(f"[STORAGE] No se pudo eliminar {carpeta}: {error}")
        return

    print(f"[STORAGE] Carpeta eliminada: {carpeta}")