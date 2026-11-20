import json
import unicodedata
from difflib import SequenceMatcher

from app.database.connection import get_connection

TITULO = "Formularios de Convocatorias abiertas"


def _opciones(valor):
    if isinstance(valor, list):
        return [str(item) for item in valor if str(item).strip()]
    if isinstance(valor, str):
        try:
            cargado = json.loads(valor)
        except json.JSONDecodeError:
            return []
        return _opciones(cargado)
    return []


def _mapa(valor):
    if isinstance(valor, str):
        try:
            valor = json.loads(valor)
        except json.JSONDecodeError:
            return {}
    if not isinstance(valor, dict):
        return {}
    mapa = {}
    for clave, lista in valor.items():
        opciones = _opciones(lista)
        texto = str(clave).strip()
        if texto and opciones:
            mapa[texto] = opciones
    return mapa


def _columnas(valor):
    if isinstance(valor, str):
        try:
            valor = json.loads(valor)
        except json.JSONDecodeError:
            return []
    if not isinstance(valor, list):
        return []
    columnas = []
    for item in valor:
        if not isinstance(item, dict):
            continue
        etiqueta = str(item.get("etiqueta") or "").strip()
        selector = str(item.get("selector") or "").strip()
        if not etiqueta or not selector:
            continue
        columnas.append(
            {
                "etiqueta": etiqueta,
                "tipo": str(item.get("tipo") or "text").strip() or "text",
                "requerido": bool(item.get("requerido")),
                "opciones": _opciones(item.get("opciones")),
                "selector": selector,
                "depende_de": item.get("depende_de"),
                "opciones_por_valor": _mapa(item.get("opciones_por_valor")),
            }
        )
    return columnas


def _clave_columna(etiqueta: str) -> str:
    return " ".join(str(etiqueta).replace("*", " ").split()).casefold()


def filas_de_tabla(respuesta, columnas) -> list[dict]:
    """Deja solo filas con datos y encaja cada celda en una columna de la tabla."""
    datos = respuesta
    if isinstance(datos, str):
        texto = datos.strip()
        if not texto or texto.lower() == "null":
            return []
        try:
            datos = json.loads(texto)
        except json.JSONDecodeError:
            return []
    if isinstance(datos, dict):
        datos = [datos]
    if not isinstance(datos, list):
        return []

    filas = []
    for item in datos:
        if not isinstance(item, dict):
            continue
        crudo = {
            _clave_columna(clave): valor
            for clave, valor in item.items()
        }
        fila = {}
        for columna in columnas:
            valor = crudo.get(_clave_columna(columna["etiqueta"]))
            texto = "" if valor is None else str(valor).strip()
            if texto.lower() == "null":
                texto = ""
            opciones = list(columna.get("opciones") or [])
            mapa = columna.get("opciones_por_valor") or {}
            depende_de = columna.get("depende_de")
            if depende_de and mapa:
                padre = next(
                    (candidata for candidata in columnas if candidata.get("selector") == depende_de),
                    None,
                )
                padre_valor = fila.get(padre["etiqueta"], "") if padre else ""
                opciones = list(mapa.get(padre_valor) or [])
            if opciones and texto:
                texto = opcion_mas_parecida(texto, opciones) or ""
            fila[columna["etiqueta"]] = texto
        if any(fila.values()):
            filas.append(fila)
    return filas[:30]


def _comparable(texto: str) -> str:
    sin_tilde = unicodedata.normalize("NFD", texto)
    sin_tilde = "".join(
        caracter for caracter in sin_tilde if unicodedata.category(caracter) != "Mn"
    )
    return " ".join(sin_tilde.lower().replace("-", " ").split())


def opcion_mas_parecida(respuesta, opciones) -> str | None:
    """Elige la opción del combobox más cercana a lo que respondió el consultor."""
    if respuesta is None or not opciones:
        return None
    buscado = _comparable(str(respuesta))
    if not buscado or buscado in {"null", "none", "n/a"}:
        return None

    mejor = None
    mejor_puntaje = 0.0
    for opcion in opciones:
        candidato = _comparable(str(opcion))
        if not candidato:
            continue
        if candidato == buscado:
            return str(opcion)
        puntaje = SequenceMatcher(None, buscado, candidato).ratio()
        if buscado in candidato or candidato in buscado:
            puntaje = max(puntaje, 0.85)
        codigo = candidato.split(" ", 1)[0]
        if len(codigo) == 1 and (buscado == codigo or buscado.startswith(f"{codigo} ")):
            puntaje = max(puntaje, 0.9)
        palabras_buscadas = {palabra for palabra in buscado.split() if len(palabra) > 2}
        palabras_opcion = {palabra for palabra in candidato.split() if len(palabra) > 2}
        comunes = palabras_buscadas & palabras_opcion
        if comunes and palabras_buscadas:
            puntaje = max(puntaje, 0.55 + 0.4 * (len(comunes) / len(palabras_buscadas)))
        if puntaje > mejor_puntaje:
            mejor_puntaje = puntaje
            mejor = str(opcion)

    if mejor is None or mejor_puntaje < 0.55:
        return None
    return mejor


def metadatos_del_job(job_id: int) -> list[dict]:
    """Opciones de cada campo, en el orden del formulario de ANDE."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.etiqueta,
                    c.selector,
                    c.opciones,
                    c.depende_de,
                    c.opciones_por_valor,
                    c.columnas
                FROM formulario_job j
                JOIN formularios_campos c ON c.formulario_id = j.formulario_ande_id
                WHERE j.id = %s
                ORDER BY c.orden
                """,
                (job_id,),
            )
            filas = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "etiqueta": etiqueta,
            "selector": selector,
            "opciones": _opciones(opciones),
            "depende_de": depende_de,
            "opciones_por_valor": _mapa(opciones_por_valor),
            "columnas": _columnas(columnas),
        }
        for etiqueta, selector, opciones, depende_de, opciones_por_valor, columnas in filas
    ]


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
                    c.selector,
                    c.depende_de,
                    c.opciones_por_valor,
                    c.columnas
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
        depende_de,
        opciones_por_valor,
        columnas,
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
                "depende_de": depende_de,
                "opciones_por_valor": _mapa(opciones_por_valor),
                "columnas": _columnas(columnas),
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
                SELECT etiqueta, tipo, opciones, selector, depende_de, opciones_por_valor, columnas
                FROM formularios_campos
                WHERE formulario_id = %s
                ORDER BY orden
                """,
                (formulario_id,),
            )
            filas = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "campo": etiqueta,
            "tipo": tipo,
            "opciones": _opciones(opciones),
            "selector": selector,
            "depende_de": depende_de,
            "opciones_por_valor": _mapa(opciones_por_valor),
            "columnas": _columnas(columnas),
        }
        for etiqueta, tipo, opciones, selector, depende_de, opciones_por_valor, columnas in filas
    ]
