from app.database.connection import get_connection


def obtener_proyectos(buscar: str | None = None, limit: int = 50):
    conn = get_connection()
    cursor = conn.cursor()

    where = ""
    parametros = []

    if buscar is not None and buscar.strip() != "":
        where = """
            AND (
                nombre ILIKE %s
                OR COALESCE(estado, '') ILIKE %s
                OR COALESCE(anio, '') ILIKE %s
                OR COALESCE(descripcion, '') ILIKE %s
                OR COALESCE(investigadores, '') ILIKE %s
            )
        """
        patron = f"%{buscar.strip()}%"
        parametros.extend([patron] * 5)

    cursor.execute(
        f"""
        SELECT
            id,
            nombre,
            estado,
            anio,
            descripcion,
            investigadores,
            creado
        FROM proyectos
        WHERE 1=1
        {where}
        ORDER BY id DESC
        LIMIT %s
        """,
        parametros + [limit],
    )

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    proyectos = []

    for row in rows:
        proyectos.append({
            "id": row[0],
            "nombre": row[1],
            "estado": row[2],
            "anio": row[3],
            "descripcion": row[4],
            "investigadores": row[5],
            "creado": row[6],
        })

    return proyectos
