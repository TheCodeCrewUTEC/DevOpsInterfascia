from app.database.connection import get_connection


def obtener_investigadores(buscar: str | None = None, limit: int = 50):
    conn = get_connection()
    cursor = conn.cursor()

    where = ""
    parametros = []

    if buscar is not None and buscar.strip() != "":
        where = """
            AND (
                nombre ILIKE %s
                OR apellido ILIKE %s
                OR COALESCE(institucion, '') ILIKE %s
                OR COALESCE(titulo, '') ILIKE %s
                OR COALESCE(investigaciones, '') ILIKE %s
                OR COALESCE(nivel_sni, '') ILIKE %s
                OR COALESCE(categoria_sni, '') ILIKE %s
            )
        """
        patron = f"%{buscar.strip()}%"
        parametros.extend([patron] * 7)

    cursor.execute(
        f"""
        SELECT
            id,
            nombre,
            apellido,
            institucion,
            titulo,
            investigaciones,
            nivel_sni,
            categoria_sni,
            creado
        FROM investigadores
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

    investigadores = []

    for row in rows:
        investigadores.append({
            "id": row[0],
            "nombre": row[1],
            "apellido": row[2],
            "institucion": row[3],
            "titulo": row[4],
            "investigaciones": row[5],
            "nivel_sni": row[6],
            "categoria_sni": row[7],
            "creado": row[8],
        })

    return investigadores
