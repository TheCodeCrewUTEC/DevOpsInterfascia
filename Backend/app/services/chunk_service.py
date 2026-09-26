from app.database.connection import get_connection


def obtener_chunks():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            documento_id,
            contenido,
            pagina,
            embedding,
            creado
        FROM chunk
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    chunks = []

    for row in rows:
        chunks.append({
            "id": row[0],
            "documento_id": row[1],
            "contenido": row[2],
            "pagina": row[3],
            "embedding": row[4],
            "creado": row[5]
        })

    return chunks

def obtener_chunk(id: int):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            documento_id,
            contenido,
            pagina,
            embedding,
            creado
        FROM chunk
        WHERE id = %s
    """, (id,))

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    return {
        "id": row[0],
        "documento_id": row[1],
        "contenido": row[2],
        "pagina": row[3],
        "embedding": row[4],
        "creado": row[5]
    }

def obtener_chunk_por_documento(documento_id: int):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            documento_id,
            contenido,
            pagina,
            embedding,
            creado
        FROM chunk
        WHERE documento_id = %s
        ORDER BY id
    """, (documento_id,))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return [
        {
            "id": row[0],
            "documento_id": row[1],
            "contenido": row[2],
            "pagina": row[3],
            "embedding": row[4],
            "creado": row[5]
        }
        for row in rows
    ]

def obtener_chunks_por_documento(documento_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            documento_id,
            contenido,
            pagina,
            embedding,
            creado
        FROM chunk
        WHERE documento_id = %s
        ORDER BY id
    """, (documento_id,))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return [
        {
            "id": row[0],
            "documento_id": row[1],
            "contenido": row[2],
            "pagina": row[3],
            "embedding": row[4],
            "creado": row[5]
        }
        for row in rows
    ]