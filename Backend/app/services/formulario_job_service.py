from app.database.connection import get_connection

def crear_job(formulario_path: str | None):

    conn = get_connection()

    try:
        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO formulario_job (
                    estado,
                    formulario_path
                )
                VALUES (%s, %s)
                RETURNING id, estado, creado
                """,
                (
                    "PENDING",
                    formulario_path
                )
            )

            job = cur.fetchone()

        conn.commit()

        return {
            "id": job[0],
            "estado": job[1],
            "creado": job[2]
        }

    finally:
        conn.close()