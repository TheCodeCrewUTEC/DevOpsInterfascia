from app.database.connection import get_connection
from app.services import cache_service
from app.services.documento_service import obtener_documento_por_convocatoria
from datetime import date

# Temporal: el repositorio y Relacionar muestran solo convocatorias
# que ya tienen descripción y al menos una fecha. La analítica (RF006)
# usa la misma condición para contar lo mismo que se ve en el repositorio.
CONDICION_VISIBLE = """
    btrim(COALESCE(descripcion, '')) <> ''
    AND (
        fecha_apertura IS NOT NULL
        OR fecha_cierre IS NOT NULL
    )
"""

def obtener_convocatorias(
    estado: str | None = None,
    institucion: str | None = None,
    buscar: str | None = None,
    fecha_apertura_desde: date | None = None,
    fecha_apertura_hasta: date | None = None,
    fecha_cierre_desde: date | None = None,
    fecha_cierre_hasta: date | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    page: int = 1,
    limit: int = 20
):

    # El listado se repite mucho (repositorio, Relacionar): se guarda unos minutos en Redis
    clave_cache = cache_service.clave("convocatorias", locals())
    guardado = cache_service.leer(clave_cache)
    if guardado is not None:
        return guardado

    resultado = _consultar_convocatorias(
        estado, institucion, buscar,
        fecha_apertura_desde, fecha_apertura_hasta,
        fecha_cierre_desde, fecha_cierre_hasta,
        fecha_desde, fecha_hasta,
        page, limit,
    )
    cache_service.guardar(clave_cache, resultado)
    return resultado


def _consultar_convocatorias(
    estado, institucion, buscar,
    fecha_apertura_desde, fecha_apertura_hasta,
    fecha_cierre_desde, fecha_cierre_hasta,
    fecha_desde, fecha_hasta,
    page, limit,
):

    conn = get_connection()
    cursor = conn.cursor()

    where = ""
    parametros = []

    # Temporal (ver CONDICION_VISIBLE). Quitar esta línea para volver a listar todas.
    where += f" AND {CONDICION_VISIBLE}"

    if estado is not None:
        where += " AND LOWER(estado) LIKE LOWER(%s)"
        parametros.append(f"%{estado}%")

    if institucion is not None:
        where += " AND LOWER(institucion) LIKE LOWER(%s)"
        parametros.append(f"%{institucion}%")

    if buscar is not None and buscar.strip() != "":
        where += """
            AND (
                titulo ILIKE %s
                OR COALESCE(descripcion, '') ILIKE %s
                OR COALESCE(institucion, '') ILIKE %s
                OR COALESCE(beneficiarios, '') ILIKE %s
            )
        """
        patron = f"%{buscar.strip()}%"
        parametros.extend([patron] * 4)

    if fecha_apertura_desde is not None:
        where += " AND fecha_apertura >= %s"
        parametros.append(fecha_apertura_desde)

    if fecha_apertura_hasta is not None:
        where += " AND fecha_apertura <= %s"
        parametros.append(fecha_apertura_hasta)

    if fecha_cierre_desde is not None:
        where += " AND fecha_cierre >= %s"
        parametros.append(fecha_cierre_desde)

    if fecha_cierre_hasta is not None:
        where += " AND fecha_cierre <= %s"
        parametros.append(fecha_cierre_hasta)

    # Rango del repositorio: la convocatoria está abierta algún día entre desde y hasta.
    # Si le falta una de las fechas se usa la otra.
    if fecha_desde is not None:
        where += " AND COALESCE(fecha_cierre, fecha_apertura) >= %s"
        parametros.append(fecha_desde)

    if fecha_hasta is not None:
        where += " AND COALESCE(fecha_apertura, fecha_cierre) <= %s"
        parametros.append(fecha_hasta)

    cursor.execute(
        f"""
        SELECT COUNT(*)
        FROM convocatoria
        WHERE 1=1
        {where}
        """,
        parametros
    )

    total = cursor.fetchone()[0]

    offset = (page - 1) * limit

    cursor.execute(
        f"""
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
        WHERE 1=1
        {where}
        ORDER BY id DESC
        LIMIT %s
        OFFSET %s
        """,
        parametros + [limit, offset]
    )
    
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

    total_pages = (total + limit - 1) // limit

    return {
        "items": convocatorias,
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages
    }

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