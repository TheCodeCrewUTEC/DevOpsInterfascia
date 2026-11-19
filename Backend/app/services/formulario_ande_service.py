import json

from app.database.connection import get_connection

TITULO = "Formularios de Convocatorias abiertas"


def _opciones(valor):
    if isinstance(valor, list):
        return valor
    if isinstance(valor, str):
        try:
            cargado = json.loads(valor)
        except json.JSONDecodeError:
            return []
        return cargado if isinstance(cargado, list) else []
    return []


def listar_formularios_abiertos():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    f.id,
                    f.convocatoria,
                    f.creado,
                    c.orden,
                    c.seccion,
                    c.etiqueta,
                    c.tipo,
                    c.requerido,
                    c.opciones,
                    c.selector
                FROM formularios f
                JOIN formularios_campos c ON c.formulario_id = f.id
                ORDER BY f.convocatoria, c.orden
                """
            )
            filas = cur.fetchall()
    finally:
        conn.close()

    por_id: dict[int, dict] = {}
    for (
        formulario_id,
        convocatoria,
        creado,
        orden,
        seccion,
        etiqueta,
        tipo,
        requerido,
        opciones,
        selector,
    ) in filas:
        formulario = por_id.get(formulario_id)
        if formulario is None:
            formulario = {
                "id": formulario_id,
                "convocatoria": convocatoria,
                "obtenido": creado.isoformat() if creado is not None else None,
                "campos": [],
            }
            por_id[formulario_id] = formulario
        formulario["campos"].append(
            {
                "orden": orden,
                "seccion": seccion,
                "etiqueta": etiqueta,
                "tipo": tipo,
                "requerido": bool(requerido),
                "opciones": _opciones(opciones),
                "selector": selector,
            }
        )

    return {
        "titulo": TITULO,
        "formularios": list(por_id.values()),
    }


def campos_para_consultor(formulario_id: int):
    """Campos del formulario de ANDE, con la forma que espera el consultor.

    None si ese formulario no existe.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM formularios WHERE id = %s",
                (formulario_id,),
            )
            if cur.fetchone() is None:
                return None
            cur.execute(
                """
                SELECT etiqueta, tipo
                FROM formularios_campos
                WHERE formulario_id = %s
                ORDER BY orden
                """,
                (formulario_id,),
            )
            filas = cur.fetchall()
    finally:
        conn.close()

    return [{"campo": etiqueta, "tipo": tipo} for etiqueta, tipo in filas]
