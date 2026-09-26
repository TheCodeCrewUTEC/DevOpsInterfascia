from app.database.connection import get_connection
from app.services.documento_service import obtener_documento_por_convocatoria

def obtener_convocatorias():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            titulo,
            institucion,
            estado,
            fecha_apertura,
            fecha_cierre,
            descripcion,
            beneficiarios,
            requisitos,
            financiamiento,
            creado
        FROM convocatoria
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    convocatorias = []

    for row in rows:
        convocatorias.append({
            "id": row[0],
            "titulo": row[1],
            "institucion": row[2],
            "estado": row[3],
            "fecha_apertura": row[4],
            "fecha_cierre": row[5],
            "descripcion": row[6],
            "beneficiarios": row[7],
            "requisitos": row[8],
            "financiamiento": row[9],
            "creado": row[10]
        })

    return convocatorias

def obtener_convocatoria(id: int):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            titulo,
            institucion,
            estado,
            fecha_apertura,
            fecha_cierre,
            descripcion,
            beneficiarios,
            requisitos,
            financiamiento,
            creado
        FROM convocatoria
        WHERE id = %s
    """, (id,))

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    if row is None:
        return None

    # Obtener documentos relacionados
    documentos = obtener_documento_por_convocatoria(id)

    return {
        "id": row[0],
        "titulo": row[1],
        "institucion": row[2],
        "estado": row[3],
        "fecha_apertura": row[4],
        "fecha_cierre": row[5],
        "descripcion": row[6],
        "beneficiarios": row[7],
        "requisitos": row[8],
        "financiamiento": row[9],
        "creado": row[10],
        "documentos": documentos
    }