import secrets
import shutil
from pathlib import Path

from app.database.connection import get_connection

STORAGE_FORMULARIOS = Path("storage/formularios")

def crear_job(formulario_path: str | None, usuario_sub: str | None = None):
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
                    consulta_token
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id, estado, creado
                """,
                (
                    "PENDING",
                    formulario_path,
                    usuario_sub,
                    consulta_token,
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
                    error
                FROM formulario_job
                WHERE id = %s
                """,
                (job_id,)
            )

            job = cur.fetchone()

        return job

    finally:
        conn.close()

def actualizar_estado_job(job_id: int, estado: str):
    conn = get_connection()

    try:
        with conn.cursor() as cur:

            cur.execute(
                """
                UPDATE formulario_job
                SET estado = %s
                WHERE id = %s
                """,
                (
                    estado,
                    job_id
                )
            )

        conn.commit()

    finally:
        conn.close()

    if estado in ("COMPLETED", "FAILED"):
        eliminar_carpeta_job(job_id)


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