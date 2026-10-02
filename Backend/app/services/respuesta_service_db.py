from app.database.connection import get_connection
import json

def guardar_respuesta(
    job_id: int,
    campo: str,
    respuesta: str | None,
    fuentes: list
):

    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    INSERT INTO respuesta_formulario
                        (job_id, campo, respuesta, fuentes)
                    VALUES
                        (%s, %s, %s, %s)
                    """,
                    (
                        job_id,
                        campo,
                        respuesta,
                        json.dumps(fuentes, ensure_ascii=False),
                    )
                )

    finally:
        conn.close()