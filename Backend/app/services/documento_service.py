from app.database.connection import get_connection
from app.services.chunk_service import obtener_chunks_por_documento


def obtener_documentos():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            convocatoria_id,
            nombre,
            url,
            creado
        FROM documento
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return [
        {
            "id": row[0],
            "convocatoria_id": row[1],
            "nombre": row[2],
            "url": row[3],
            "creado": row[4]
        }
        for row in rows
    ]

def obtener_documento(id: int):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            convocatoria_id,
            nombre,
            url,
            creado
        FROM documento
        WHERE id = %s
    """, (id,))

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if row is None:
        return None

    chunks = obtener_chunks_por_documento(id)

    return {
        "id": row[0],
        "convocatoria_id": row[1],
        "nombre": row[2],
        "url": row[3],
        "creado": row[4],
        "chunks": chunks
    }

def obtener_documento_por_convocatoria(convocatoria_id: int):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            convocatoria_id,
            nombre,
            url,
            creado
        FROM documento
        WHERE convocatoria_id = %s
        ORDER BY id
    """, (convocatoria_id,))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return [
        {
            "id": row[0],
            "convocatoria_id": row[1],
            "nombre": row[2],
            "url": row[3],
            "creado": row[4]
        }
        for row in rows
    ]