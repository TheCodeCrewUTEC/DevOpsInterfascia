from app.database.connection import get_connection
import json

def guardar_respuesta(
    job_id: int,
    campo: str,
    respuesta: str | None,
    fuentes: list,
    tipo: str | None = None,
    pagina: int | None = None,
):

    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:

                # respuesta_ia conserva lo que propuso la IA aunque el usuario edite
                cur.execute(
                    """
                    INSERT INTO respuesta_formulario
                        (job_id, campo, respuesta, respuesta_ia, fuentes, tipo, pagina)
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        job_id,
                        campo,
                        respuesta,
                        respuesta,
                        json.dumps(fuentes, ensure_ascii=False),
                        tipo,
                        pagina,
                    )
                )

    finally:
        conn.close()


def actualizar_respuestas(job_id: int, cambios: list[dict]) -> int:
    """Guarda las correcciones del usuario. Devuelve cuántos campos se actualizaron."""

    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:

                total = 0

                for cambio in cambios:
                    cur.execute(
                        """
                        UPDATE respuesta_formulario
                        SET respuesta = %s,
                            editada = %s IS DISTINCT FROM respuesta_ia
                        WHERE id = %s AND job_id = %s
                        """,
                        (
                            cambio["respuesta"],
                            cambio["respuesta"],
                            cambio["id"],
                            job_id,
                        )
                    )
                    total += cur.rowcount

                return total

    finally:
        conn.close()
