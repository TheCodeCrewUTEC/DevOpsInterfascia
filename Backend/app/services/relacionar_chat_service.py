import json
import re
import threading
import unicodedata
from pathlib import Path

from langchain_ollama import ChatOllama
from psycopg2.extras import Json

from app.database.connection import get_connection
from app.services.relacionar_service import (
    MODEL_NAME,
    OLLAMA_URL,
    RelacionarError,
    _abierta,
    _catalogo_convocatorias,
    _fondos_cercanos,
    _leer_json,
    _modelo_embedding,
    _recortar,
    _similitud,
    _trabajo,
)

llm_breve = ChatOllama(
    model=MODEL_NAME,
    temperature=0,
    num_ctx=8192,
    num_predict=1000,
    base_url=OLLAMA_URL,
)

STORAGE = Path("storage/relacionar")
PREGUNTA_INICIAL = (
    "Ya leí los documentos. ¿Qué querés saber? "
    "Puedo recomendarte fondos para que los abras, "
    "o responderte algo puntual."
)

_fragmentos: dict[int, list[dict]] = {}
_fragmentos_lock = threading.Lock()


def carpeta_conversacion(conversacion_id: int) -> Path:
    return STORAGE / f"conv_{conversacion_id}"


def preparar_base() -> None:
    """Carga el catálogo de fondos mientras Docling lee los documentos."""

    def _cargar() -> None:
        with _trabajo:
            _catalogo_convocatorias()

    threading.Thread(target=_cargar, daemon=True).start()


def crear_conversacion(usuario_sub: str, documentos: list[str]) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO relacionar_conversacion (usuario_sub, estado, documentos)
                VALUES (%s, 'PENDING', %s)
                RETURNING id, estado
                """,
                (usuario_sub, documentos),
            )
            fila = cur.fetchone()
        conn.commit()
    finally:
        conn.close()

    return {"id": fila[0], "estado": fila[1], "documentos": documentos, "mensajes": []}


def marcar_procesando(conversacion_id: int) -> None:
    _marcar(conversacion_id, "PROCESSING", None)


def marcar_lista(conversacion_id: int) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE relacionar_conversacion
                SET estado = 'READY', error = NULL, listo = NOW()
                WHERE id = %s
                """,
                (conversacion_id,),
            )
        conn.commit()
    finally:
        conn.close()


def marcar_error(conversacion_id: int, mensaje: str) -> None:
    _marcar(conversacion_id, "FAILED", mensaje)


def guardar_fragmentos(conversacion_id: int, chunks: list[dict]) -> None:
    carpeta = carpeta_conversacion(conversacion_id)
    carpeta.mkdir(parents=True, exist_ok=True)
    fragmentos = [
        {
            "documento": chunk.get("documento"),
            "pagina": chunk.get("pagina"),
            "texto": chunk.get("texto") or "",
            "embedding": chunk.get("embedding"),
        }
        for chunk in chunks
        if chunk.get("texto") and chunk.get("embedding")
    ]
    (carpeta / "fragmentos.json").write_text(
        json.dumps(fragmentos, ensure_ascii=False),
        encoding="utf-8",
    )
    with _fragmentos_lock:
        _fragmentos[conversacion_id] = fragmentos


def asegurar_pregunta_inicial(conversacion_id: int) -> None:
    if _mensajes(conversacion_id):
        return
    agregar_mensaje(conversacion_id, "asistente", PREGUNTA_INICIAL)


def obtener_estado(conversacion_id: int) -> str | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT estado FROM relacionar_conversacion WHERE id = %s",
                (conversacion_id,),
            )
            fila = cur.fetchone()
    finally:
        conn.close()
    return None if fila is None else fila[0]


def obtener_conversacion(conversacion_id: int, usuario_sub: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT estado, error, documentos
                FROM relacionar_conversacion
                WHERE id = %s AND usuario_sub = %s
                """,
                (conversacion_id, usuario_sub),
            )
            fila = cur.fetchone()
    finally:
        conn.close()

    if fila is None:
        return None

    return {
        "id": conversacion_id,
        "estado": fila[0],
        "error": fila[1],
        "documentos": list(fila[2] or []),
        "mensajes": _mensajes(conversacion_id),
    }


def responder(conversacion_id: int, usuario_sub: str, pregunta: str) -> dict:
    conversacion = obtener_conversacion(conversacion_id, usuario_sub)
    if conversacion is None:
        return None
    if conversacion["estado"] != "READY":
        raise RelacionarError("Todavía estoy leyendo los documentos.")

    with _trabajo:
        respuesta, fondos = _responder(conversacion_id, pregunta)
    agregar_mensaje(conversacion_id, "usuario", pregunta)
    agregar_mensaje(conversacion_id, "asistente", respuesta, fondos)
    return {"contenido": respuesta, "fondos": fondos}


def agregar_mensaje(
    conversacion_id: int,
    rol: str,
    contenido: str,
    fondos: list[dict] | None = None,
) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO relacionar_mensaje (conversacion_id, rol, contenido, fondos)
                VALUES (%s, %s, %s, %s)
                """,
                (conversacion_id, rol, contenido, Json(fondos) if fondos else None),
            )
        conn.commit()
    finally:
        conn.close()


def _marcar(conversacion_id: int, estado: str, error: str | None) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE relacionar_conversacion
                SET estado = %s, error = %s
                WHERE id = %s
                """,
                (estado, error, conversacion_id),
            )
        conn.commit()
    finally:
        conn.close()


def _fondos_guardados(valor) -> list[dict]:
    if not valor:
        return []
    datos = json.loads(valor) if isinstance(valor, str) else valor
    if not isinstance(datos, list):
        return []
    return [item for item in datos if isinstance(item, dict)]


def _mensajes(conversacion_id: int) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT rol, contenido, fondos
                FROM relacionar_mensaje
                WHERE conversacion_id = %s
                ORDER BY id
                """,
                (conversacion_id,),
            )
            filas = cur.fetchall()
    finally:
        conn.close()

    return [
        {"rol": rol, "contenido": contenido, "fondos": _fondos_guardados(fondos)}
        for rol, contenido, fondos in filas
    ]


def _cargar_fragmentos(conversacion_id: int) -> list[dict]:
    with _fragmentos_lock:
        if conversacion_id in _fragmentos:
            return _fragmentos[conversacion_id]

    ruta = carpeta_conversacion(conversacion_id) / "fragmentos.json"
    if not ruta.is_file():
        return []
    fragmentos = json.loads(ruta.read_text(encoding="utf-8"))
    with _fragmentos_lock:
        _fragmentos[conversacion_id] = fragmentos
    return fragmentos


def _resumen_proyecto(fragmentos: list[dict]) -> str:
    vistos = set()
    partes = []
    for fragmento in fragmentos:
        documento = fragmento.get("documento") or "documento"
        if documento in vistos:
            continue
        vistos.add(documento)
        partes.append(f"{documento}: {_recortar(fragmento.get('texto'), 700)}")
        if len(vistos) >= 3:
            break
    return "\n".join(partes)


def _fragmentos_de_la_pregunta(fragmentos: list[dict], vector) -> str:
    ordenados = sorted(
        fragmentos,
        key=lambda fragmento: _similitud(vector, fragmento["embedding"]),
        reverse=True,
    )
    lineas = []
    for fragmento in ordenados[:5]:
        pagina = fragmento.get("pagina")
        donde = fragmento.get("documento") or "documento"
        if pagina:
            donde = f"{donde}, p. {pagina}"
        lineas.append(f"- {donde}: {_recortar(fragmento.get('texto'), 700)}")
    return "\n".join(lineas)


def _vector_pg(vector) -> str:
    return "[" + ",".join(f"{float(valor):.8f}" for valor in vector) + "]"


def _extractos_fondos(fondos: list[dict], vector) -> str:
    ids = [fondo["id"] for fondo in fondos]
    if not ids:
        return ""

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.titulo, ch.pagina, ch.contenido
                FROM chunk ch
                INNER JOIN documento d ON d.id = ch.documento_id
                INNER JOIN convocatoria c ON c.id = d.convocatoria_id
                WHERE c.id = ANY(%s)
                  AND ch.embedding IS NOT NULL
                ORDER BY ch.embedding <=> CAST(%s AS vector)
                LIMIT 6
                """,
                (ids, _vector_pg(vector)),
            )
            filas = cur.fetchall()
    finally:
        conn.close()

    lineas = []
    vistos = set()
    for titulo, pagina, contenido in filas:
        nombre = titulo or "Fondo"
        if nombre in vistos:
            continue
        vistos.add(nombre)
        donde = f"{nombre}, p. {pagina}" if pagina else nombre
        lineas.append(f"- {donde}: {_recortar(contenido, 280)}")
    return "\n".join(lineas)


_MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "setiembre", "octubre", "noviembre", "diciembre",
)


def _fecha_legible(valor) -> str | None:
    texto = str(valor or "")[:10]
    partes = texto.split("-")
    if len(partes) != 3 or not all(parte.isdigit() for parte in partes):
        return None
    anio, mes, dia = partes
    return f"{dia}/{mes}/{anio}"


def _formas_fecha(valor) -> list[str]:
    texto = str(valor or "")[:10]
    partes = texto.split("-")
    if len(partes) != 3 or not all(parte.isdigit() for parte in partes):
        return []
    anio, mes, dia = partes
    dia_corto = str(int(dia))
    mes_corto = str(int(mes))
    nombre = _MESES[int(mes) - 1]
    formas = [
        f"{anio}-{mes}-{dia}",
        f"{dia}/{mes}/{anio}",
        f"{dia_corto}/{mes_corto}/{anio}",
        f"{dia}-{mes}-{anio}",
        f"{dia_corto} de {nombre} de {anio}",
        f"{dia} de {nombre} de {anio}",
    ]
    if nombre == "setiembre":
        formas.extend([
            f"{dia_corto} de septiembre de {anio}",
            f"{dia} de septiembre de {anio}",
        ])
    return formas


def _tipo_fecha(pregunta: str) -> str | None:
    texto = _normalizar(pregunta)
    abre = any(
        marca in texto
        for marca in (
            "fecha de inicio",
            "fecha de apertura",
            "cuando abre",
            "cuando empieza",
            "cuando se abre",
            "a partir de cuando",
            "desde cuando",
        )
    )
    cierra = any(
        marca in texto
        for marca in (
            "fecha de cierre",
            "cuando cierra",
            "hasta cuando",
            "fecha limite",
            "cuando vence",
        )
    )
    if abre and cierra:
        return "ambas"
    if abre:
        return "apertura"
    if cierra:
        return "cierre"
    return None


def _respuesta_fecha(fondo: dict, tipo: str) -> str:
    titulo = fondo.get("titulo") or "Ese fondo"
    abre = _fecha_legible(fondo.get("fecha_apertura"))
    cierra = _fecha_legible(fondo.get("fecha_cierre"))
    if tipo == "apertura":
        if not abre:
            return f"No hay una fecha de apertura cargada para {titulo}."
        return f"{titulo} abre el {abre}."
    if tipo == "cierre":
        if not cierra:
            return f"No hay una fecha de cierre cargada para {titulo}."
        return f"{titulo} cierra el {cierra}."
    partes = []
    if abre:
        partes.append(f"abre el {abre}")
    if cierra:
        partes.append(f"cierra el {cierra}")
    if not partes:
        return f"No hay fechas cargadas para {titulo}."
    return f"{titulo} " + " y ".join(partes) + "."


def _corregir_fechas(texto: str, fondo: dict, otros: list[dict]) -> str:
    for otro in otros:
        if otro.get("id") == fondo.get("id"):
            continue
        pares = (
            (otro.get("fecha_apertura"), fondo.get("fecha_apertura")),
            (otro.get("fecha_cierre"), fondo.get("fecha_cierre")),
        )
        for ajena, propia in pares:
            if not ajena or not propia or str(ajena)[:10] == str(propia)[:10]:
                continue
            destino = _fecha_legible(propia)
            if not destino:
                continue
            for forma in _formas_fecha(ajena):
                texto = texto.replace(forma, destino)
    return texto


def _linea_fondo(fondo: dict) -> str:
    abre = _fecha_legible(fondo.get("fecha_apertura"))
    cierra = _fecha_legible(fondo.get("fecha_cierre"))
    fechas = []
    if abre:
        fechas.append(f"abre el {abre}")
    if cierra:
        fechas.append(f"cierra el {cierra}")
    plazo = ". ".join(fechas)
    dato = _recortar(fondo.get("requisitos") or fondo.get("descripcion") or "", 220)
    return (
        f"- {fondo.get('titulo') or 'Fondo'}. "
        f"Estado: {fondo.get('estado') or 'sin estado'}. "
        f"{plazo + '. ' if plazo else ''}{dato}"
        f"Campo id del JSON, no lo escribas en la respuesta: {fondo['id']}."
    )


def _tarjeta(fondo: dict, motivo: str | None = None) -> dict:
    return {
        "id": fondo["id"],
        "titulo": fondo.get("titulo"),
        "estado": fondo.get("estado"),
        "motivo": _recortar(_sin_id(motivo), 140) if motivo else None,
    }


def _tarjetas(fondos: list[dict], elegidos: list[dict], completar: bool) -> list[dict]:
    por_id = {fondo["id"]: fondo for fondo in fondos}
    tarjetas = []
    vistos = set()
    for item in elegidos:
        if not isinstance(item, dict):
            continue
        fondo = por_id.get(item.get("id"))
        if fondo is None or fondo["id"] in vistos:
            continue
        vistos.add(fondo["id"])
        tarjetas.append(_tarjeta(fondo, str(item.get("motivo") or "")))
        if len(tarjetas) == 3:
            break
    if tarjetas or not completar:
        tarjetas.sort(key=lambda tarjeta: 0 if _abierta(tarjeta.get("estado")) else 1)
        return tarjetas

    for fondo in fondos:
        if not _abierta(fondo.get("estado")) and any(_abierta(otro.get("estado")) for otro in fondos):
            continue
        tarjetas.append(_tarjeta(fondo, "Se acerca al tema de tu proyecto."))
        if len(tarjetas) == 3:
            break
    return tarjetas


def _tarjetas_explicadas(fondos: list[dict], pedidos) -> list[dict]:
    motivos = {}
    if isinstance(pedidos, list):
        for item in pedidos:
            if isinstance(item, dict) and item.get("id") is not None:
                motivos[item["id"]] = item.get("motivo")
    return [
        _tarjeta(fondo, str(motivos.get(fondo["id"]) or ""))
        for fondo in fondos[:3]
    ]


def _sin_id(texto: str) -> str:
    limpio = re.sub(r"(?i)\(\s*id\s*[:.]?\s*\d+\s*\)", "", texto or "")
    limpio = re.sub(r"(?i)\(\s*fondo\s+\d+\s*\)", "", limpio)
    limpio = re.sub(r"(?i)\b(id|identificador)\s*[:.#-]?\s*\d+\b", "", limpio)
    limpio = re.sub(r"(?i)\bfondo\s+\d+\b", "", limpio)
    limpio = re.sub(r"\(\s*\)", "", limpio)
    limpio = re.sub(r"[^\S\n]+([,.;:])", r"\1", limpio)
    limpio = re.sub(r"[^\S\n]{2,}", " ", limpio)
    limpio = re.sub(r" *\n *", "\n", limpio)
    return limpio.strip()


def _texto_plano(texto: str) -> str:
    limpio = re.sub(r"\*\*|__", "", texto)
    limpio = re.sub(r"(?m)^#{1,6}\s*", "", limpio)
    return _sin_id(limpio)


def _extraer_texto(crudo: str, datos: dict) -> str:
    texto = str(datos.get("texto") or "").strip()
    if texto:
        return texto
    coincidencia = re.search(r'"texto"\s*:\s*"', crudo)
    if not coincidencia:
        if crudo.strip().startswith("{"):
            return ""
        return crudo
    chars = []
    escapado = False
    for char in crudo[coincidencia.end():]:
        if escapado:
            chars.append({"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}.get(char, char))
            escapado = False
            continue
        if char == "\\":
            escapado = True
            continue
        if char == '"':
            break
        chars.append(char)
    salida = "".join(chars).strip()
    return re.split(r'\s*"\s*,?\s*"fondos"\s*:', salida)[0].strip().rstrip(",").strip()


def _formatear_lista(texto: str) -> str:
    texto = re.sub(
        r"(?m)(?:^|(?<=[.!?:;\n]))[ \t]*[-–—•][ \t]+(?=[A-ZÁÉÍÓÚÑ¿])",
        "\n- ",
        texto,
    )
    if len(re.findall(r"(?:^|\s)\d{1,2}[.)]\s+\S", texto)) >= 2:
        texto = re.sub(
            r"(?m)(?<!\d)(?:^|(?<=\s))(\d{1,2})[.)][ \t]+",
            r"\n\1. ",
            texto,
        )
    texto = "\n".join(linea.rstrip() for linea in texto.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", texto).strip()


def _acortar(texto: str, detalle: bool = False, limite: int | None = None) -> str:
    limpio = _texto_plano(texto)
    limpio = re.sub(r"(?i)\b(?:el\s+)?fondo\s+id\s+\d+\s*\|\s*[^|.]+\|\s*", "", limpio)
    limpio = re.sub(r"[^\S\n]{2,}", " ", limpio).strip()
    limpio = _formatear_lista(limpio)
    if limite is None:
        limite = 2200 if detalle else 420
    if detalle:
        if len(limpio) <= limite:
            return limpio
        corte = limpio[:limite]
        salto = corte.rfind("\n")
        if salto > 80:
            return corte[:salto].rstrip()
        return corte.rsplit(" ", 1)[0].rstrip(" ,;:") + "…"

    partes = [parte.strip() for parte in re.split(r"(?<=[.!?])\s+", limpio) if parte.strip()]
    if not partes:
        recorte = limpio[:limite].rsplit(" ", 1)[0].rstrip() if len(limpio) > limite else limpio
        return _formatear_lista(recorte)

    elegido = []
    for parte in partes[:3]:
        propuesta = " ".join(elegido + [parte])
        if len(propuesta) > limite and elegido:
            break
        elegido.append(parte)
    corto = " ".join(elegido)
    if len(corto) > limite:
        corto = corto[:limite].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"
    return _formatear_lista(corto)


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto or "")
    sin_tildes = "".join(letra for letra in sin_tildes if not unicodedata.combining(letra))
    return re.sub(r"\s+", " ", sin_tildes).casefold().strip()


def _pide_el_otro(pregunta: str) -> bool:
    texto = _normalizar(pregunta)
    return any(marca in texto for marca in ("el otro", "la otra", "los otros", "las otras"))


def _pide_el_grupo(pregunta: str) -> bool:
    texto = _normalizar(pregunta)
    return any(
        marca in texto
        for marca in (
            "esos",
            "esas",
            "estos",
            "estas",
            "ambos",
            "ambas",
            "los dos",
            "las dos",
            "cada uno",
            "cada una",
        )
    )


def _pide_requisitos(pregunta: str) -> bool:
    return "requisit" in _normalizar(pregunta)


def _pide_proceso(pregunta: str) -> bool:
    texto = _normalizar(pregunta)
    return (
        "proceso de postul" in texto
        or "proceso de present" in texto
        or ("como" in texto and "postul" in texto)
        or ("pasos" in texto and "postul" in texto)
    )


_PROCESO_MARCAS = (
    r"postulaci[oó]n deber[aá]",
    r"formulario provisto",
    r"se considera realizada",
    r"c[oó]mo postular",
    r"para postular",
)


def _puntaje_proceso(contenido: str) -> int:
    texto = _normalizar(contenido)
    puntos = 0
    fuerte = False
    if "postulacion debera" in texto:
        puntos += 20
        fuerte = True
    if "formulario provisto" in texto or "se considera realizada" in texto:
        puntos += 20
        fuerte = True
    if "como postular" in texto:
        puntos += 12
        fuerte = True
    if "para postular" in texto:
        puntos += 2
    if "formulario" in texto and "postul" in texto:
        puntos += 3
    if "postul" in texto:
        puntos += 1
    if fuerte and re.search(r"(?m)^\s*\d+[.)]\s+\S", contenido or ""):
        puntos += 2
    return puntos


def _recorte_proceso(contenido: str, limite: int = 900) -> str:
    limpio = re.sub(r"<!--.*?-->", " ", contenido or "", flags=re.S)
    limpio = re.sub(r"[ \t]{2,}", " ", limpio)
    limpio = re.sub(r"\n{3,}", "\n\n", limpio).strip()
    inicio = 0
    for patron in _PROCESO_MARCAS:
        hallazgo = re.search(patron, limpio, flags=re.I)
        if hallazgo:
            corte = limpio.rfind("\n", 0, hallazgo.start())
            inicio = 0 if corte == -1 else corte + 1
            break
    recorte = limpio[inicio:inicio + limite].strip()
    evaluacion = re.search(
        r"\n#{0,3}\s*(?:\d+\.\s*)?(evaluaci[oó]n\b|criterios de evaluaci[oó]n|¿c[oó]mo es el proceso de evaluaci[oó]n)",
        recorte,
        flags=re.I,
    )
    if evaluacion and evaluacion.start() > 40:
        recorte = recorte[:evaluacion.start()].strip()
    return recorte


def _material_proceso(fondos: list[dict]) -> tuple[list[tuple[str, str | None]], bool]:
    ids = [fondo["id"] for fondo in fondos]
    if not ids:
        return "No hay fondos en el hilo.", False

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, ch.contenido
                FROM chunk ch
                INNER JOIN documento d ON d.id = ch.documento_id
                INNER JOIN convocatoria c ON c.id = d.convocatoria_id
                WHERE c.id = ANY(%s)
                  AND ch.contenido ILIKE '%%postul%%'
                """,
                (ids,),
            )
            filas = cur.fetchall()
    finally:
        conn.close()

    por_id: dict[int, list[str]] = {}
    for fondo_id, contenido in filas:
        por_id.setdefault(fondo_id, []).append(contenido or "")

    bloques = []
    hay = False
    for fondo in fondos:
        titulo = fondo.get("titulo") or "Ese fondo"
        candidatos = sorted(
            por_id.get(fondo["id"], []),
            key=_puntaje_proceso,
            reverse=True,
        )
        elegido = None
        for texto in candidatos:
            if _puntaje_proceso(texto) < 12:
                continue
            pasos = _pasos_proceso(texto)
            if pasos and (elegido is None or len(pasos) > len(elegido)):
                elegido = pasos
                mejor = texto
        if elegido is None:
            bloques.append((titulo, None))
            continue
        hay = True
        bloques.append((titulo, mejor))
    return bloques, hay


def _limpiar_linea(linea: str) -> str:
    limpia = re.sub(r"<!--.*?-->", "", linea or "")
    limpia = re.sub(r"\b1ANE\b", "", limpia)
    limpia = re.sub(r"\s+\d{1,2}\s*$", "", limpia)
    return re.sub(r"\s+", " ", limpia).strip(" -")


def _pasos_proceso(contenido: str) -> list[str]:
    recorte = _recorte_proceso(contenido)
    numeradas = []
    for linea in recorte.splitlines():
        limpia = _limpiar_linea(linea)
        coincidencia = re.match(r"^\d+[.)]\s+(\S.*)$", limpia)
        if coincidencia:
            numeradas.append(coincidencia.group(1).strip())
    if len(numeradas) >= 2:
        return numeradas
    prosa = " ".join(
        limpia
        for linea in recorte.splitlines()
        if (limpia := _limpiar_linea(linea)) and not limpia.startswith("#")
    )
    return [
        parte.strip()
        for parte in re.split(r"(?<=[.!?])\s+", prosa)
        if len(parte.strip()) > 40
    ][:4]


def _respuesta_proceso(fondos: list[dict]) -> str:
    bloques, _hay = _material_proceso(fondos)
    salida = []
    for titulo, contenido in bloques:
        if not contenido:
            salida.append(f"{titulo}\n\nEn las bases cargadas no aparece el trámite de postulación.")
            continue
        pasos = _pasos_proceso(contenido)
        if not pasos:
            salida.append(f"{titulo}\n\nEn las bases cargadas no aparece el trámite de postulación.")
            continue
        recorte = _recorte_proceso(contenido)
        primera = _limpiar_linea(recorte.splitlines()[0]) if recorte.strip() else ""
        intro = ""
        if (
            primera
            and not re.match(r"^\d+[.)]", primera)
            and len(pasos) >= 2
            and not any(paso in primera for paso in pasos)
        ):
            intro = primera + "\n\n"
        items = "\n".join(f"{numero}. {paso}" for numero, paso in enumerate(pasos, 1))
        salida.append(f"{titulo}\n\n{intro}{items}")
    return "\n\n".join(salida)


def _respuesta_requisitos(fondos: list[dict]) -> str:
    bloques = []
    for fondo in fondos:
        titulo = fondo.get("titulo") or "Ese fondo"
        lineas = []
        for linea in (fondo.get("requisitos") or "").splitlines():
            limpia = linea.strip().lstrip("-–—•").strip()
            if limpia:
                lineas.append(f"- {limpia}")
        if lineas:
            bloques.append(titulo + "\n\n" + "\n".join(lineas))
        else:
            bloques.append(f"{titulo}\n\nNo hay requisitos cargados para este fondo.")
    return "\n\n".join(bloques)


def _fondo_recien_nombrado(conversacion_id: int) -> int | None:
    for mensaje in reversed(_mensajes(conversacion_id)):
        if mensaje["rol"] == "asistente" and mensaje["fondos"]:
            return mensaje["fondos"][0]["id"]
    return None


def _recomendados(conversacion_id: int) -> list[dict]:
    grupo = []
    for mensaje in _mensajes(conversacion_id):
        if mensaje["rol"] == "asistente" and len(mensaje["fondos"]) >= 2:
            grupo = mensaje["fondos"]
    return _resolver_fondos(grupo)


def _pide_detalle(pregunta: str) -> bool:
    texto = _normalizar(pregunta)
    return any(
        marca in texto
        for marca in (
            "explic",
            "detall",
            "por que",
            "porque",
            "cada uno",
            "cada una",
            "amplia",
            "desarroll",
            "contame mas",
        )
    )


def _pide_fondos_nuevos(pregunta: str) -> bool:
    if _pide_detalle(pregunta):
        return False
    texto = _normalizar(pregunta)
    return any(
        marca in texto
        for marca in (
            "que fondos",
            "cuales fondos",
            "otros fondos",
            "otras convocatoria",
            "mas fondos",
            "se adecu",
            "a que me puedo postular",
            "a que puedo postular",
            "recomiendame",
            "recomienda fondos",
            "recomendar fondos",
            "que me recomiendes",
            "alternativ",
        )
    )


def _puntaje_titulo(pregunta: str, titulo: str | None) -> int:
    consulta = _normalizar(pregunta)
    nombre = _normalizar(titulo)
    if len(nombre) < 4 or len(consulta) < 4:
        return 0
    if nombre in consulta:
        return 100 + len(nombre)
    palabras = [palabra for palabra in nombre.split() if len(palabra) > 4 and palabra in consulta]
    if len(palabras) >= 2:
        return len(palabras)
    return 0


def _mejor_nombrado(pregunta: str, candidatos: list[dict], preferidos: list[dict]) -> list[dict]:
    puntajes = [
        (_puntaje_titulo(pregunta, fondo.get("titulo")), fondo)
        for fondo in candidatos
    ]
    puntajes = [(puntos, fondo) for puntos, fondo in puntajes if puntos]
    if not puntajes:
        return []
    mejor = max(puntos for puntos, _fondo in puntajes)
    empatados = [fondo for puntos, fondo in puntajes if puntos == mejor]
    preferidos_ids = {fondo["id"] for fondo in preferidos}
    en_hilo = [fondo for fondo in empatados if fondo["id"] in preferidos_ids]
    return (en_hilo or empatados)[:1]


def _menciona_fondo(pregunta: str, titulo: str | None) -> bool:
    consulta = _normalizar(pregunta)
    nombre = _normalizar(titulo)
    if len(nombre) < 4 or len(consulta) < 4:
        return False
    if nombre in consulta or consulta in nombre:
        return True
    palabras = [palabra for palabra in nombre.split() if len(palabra) > 4]
    if not palabras:
        return False
    return sum(palabra in consulta for palabra in palabras) >= min(2, len(palabras))


def _resolver_fondos(tarjetas: list[dict]) -> list[dict]:
    catalogo = {fondo["id"]: fondo for fondo in _catalogo_convocatorias()}
    resueltos = []
    vistos = set()
    for tarjeta in tarjetas:
        fondo_id = tarjeta.get("id")
        if fondo_id in vistos:
            continue
        vistos.add(fondo_id)
        fondo = catalogo.get(fondo_id)
        if fondo is None:
            fondo = {
                "id": fondo_id,
                "titulo": tarjeta.get("titulo"),
                "estado": tarjeta.get("estado"),
                "fecha_cierre": None,
                "requisitos": None,
                "descripcion": None,
            }
        resueltos.append(fondo)
    return resueltos


def _fondos_del_hilo(conversacion_id: int) -> tuple[list[dict], list[dict]]:
    """Devuelve (último grupo mostrado, todos los citados en la conversación)."""
    ultimo = []
    citados = []
    for mensaje in _mensajes(conversacion_id):
        if mensaje["rol"] != "asistente" or not mensaje["fondos"]:
            continue
        ultimo = mensaje["fondos"]
        citados.extend(mensaje["fondos"])
    return _resolver_fondos(ultimo), _resolver_fondos(citados)


def _historial(conversacion_id: int) -> str:
    recientes = _mensajes(conversacion_id)[-6:]
    lineas = []
    for mensaje in recientes:
        quien = "Consultor" if mensaje["rol"] == "asistente" else "Usuario"
        linea = f"{quien}: {_recortar(_sin_id(mensaje['contenido']), 280)}"
        nombres = [
            fondo.get("titulo")
            for fondo in mensaje["fondos"]
            if fondo.get("titulo")
        ]
        if nombres:
            linea += " Fondos de esa respuesta: " + "; ".join(nombres) + "."
        lineas.append(linea)
    return "\n".join(lineas)


def _responder(conversacion_id: int, pregunta: str) -> tuple[str, list[dict]]:
    fragmentos = _cargar_fragmentos(conversacion_id)
    if not fragmentos:
        raise RelacionarError("No quedaron fragmentos de los documentos.")

    resumen = _resumen_proyecto(fragmentos)
    modelo = _modelo_embedding()
    vector_pregunta = modelo.encode(
        "query: " + pregunta,
        normalize_embeddings=True,
    )
    ultimo, citados = _fondos_del_hilo(conversacion_id)
    explica = _pide_detalle(pregunta)
    grupo = "cada uno" in _normalizar(pregunta) or "cada una" in _normalizar(pregunta)
    nombrados = [] if explica and grupo else [
        fondo for fondo in citados if _menciona_fondo(pregunta, fondo.get("titulo"))
    ]
    if _pide_el_otro(pregunta) and not nombrados:
        anterior = _fondo_recien_nombrado(conversacion_id)
        grupo_recomendado = _recomendados(conversacion_id) or citados
        otros = [fondo for fondo in grupo_recomendado if fondo["id"] != anterior]
        nombrados = otros[:1]
    if not nombrados and (_pide_el_grupo(pregunta) or _pide_proceso(pregunta)):
        nombrados = (_recomendados(conversacion_id) or ultimo or citados)[:3]
    if not nombrados and not explica and not _pide_fondos_nuevos(pregunta):
        nombrados = _mejor_nombrado(pregunta, _catalogo_convocatorias(), citados)
    seguir_hilo = bool(citados) and not _pide_fondos_nuevos(pregunta)
    if explica and grupo:
        fondos = (_recomendados(conversacion_id) or ultimo or citados)[:3]
    elif explica and (ultimo or citados) and not nombrados:
        fondos = (ultimo or citados)[:3]
    elif nombrados:
        fondos = nombrados[:3]
    elif seguir_hilo:
        fondos = ultimo or citados[:3]
    else:
        vector_fondos = modelo.encode(
            "query: " + _recortar(f"{resumen}\n{pregunta}", 1500),
            normalize_embeddings=True,
        )
        fondos = _fondos_cercanos(vector_fondos)[:5]
        if explica:
            abiertas = [fondo for fondo in fondos if _abierta(fondo.get("estado"))]
            fondos = (abiertas or fondos)[:3]
    tipo_fecha = _tipo_fecha(pregunta)
    if tipo_fecha and fondos:
        texto_fecha = " ".join(_respuesta_fecha(fondo, tipo_fecha) for fondo in fondos[:3])
        return texto_fecha, [_tarjeta(fondo) for fondo in fondos[:3]]
    if _pide_requisitos(pregunta) and fondos:
        return _respuesta_requisitos(fondos[:3]), [_tarjeta(fondo) for fondo in fondos[:3]]
    if _pide_proceso(pregunta) and fondos:
        return _respuesta_proceso(fondos[:3]), [_tarjeta(fondo) for fondo in fondos[:3]]

    fichas = "\n".join(_linea_fondo(fondo) for fondo in fondos) or "No hay fondos en la base."
    if explica:
        limite = (
            "En fondos incluí el id de cada fondo de la lista, con un motivo de una oración. "
            "No agregues fondos que no estén en la lista."
        )
        regla_texto = (
            "La persona pidió una explicación. Por cada fondo de la lista, escribí dos oraciones completas "
            "sobre por qué encaja con el proyecto. Nombrá cada fondo por su título. "
            "No uses la palabra id ni cortes una oración. "
            "Si listás los fondos, un renglón por fondo, y no cortes el título en el guión del nombre."
        )
    else:
        limite = (
            "La pregunta sigue el hilo. Hablá solo de los fondos listados abajo. "
            "No menciones ni propongas ningún otro. En fondos devolvé una lista vacía."
            if seguir_hilo or nombrados
            else "Si piden una recomendación, proponé hasta 3 fondos de la lista, priorizando los abiertos. Si no piden fondos, devolvé fondos vacío."
        )
        if _pide_requisitos(pregunta):
            regla_texto = (
                "La persona pidió solo los requisitos. Para cada fondo de la lista, "
                "escribí el título y después cada requisito en su renglón. "
                "No agregues estado, fechas ni otros datos."
            )
        else:
            regla_texto = (
                "Máximo dos oraciones. No listes requisitos, documentos, pasos ni montos. "
                "Si piden fondos, decí en una oración que puede abrirlos. "
                "Si piden un dato puntual, respondé solo ese dato."
            )
    extractos = _extractos_fondos(fondos, vector_pregunta)
    proyecto = _fragmentos_de_la_pregunta(fragmentos, vector_pregunta)
    historial = _historial(conversacion_id)

    prompt = f"""Sos el consultor de Interfascia. Seguís el hilo y respondés en español.
Devolvé solo este JSON, sin markdown:
{{"texto": "la respuesta", "fondos": [{{"id": 0, "motivo": "una oración corta"}}]}}

Reglas de texto:
- {regla_texto}
- No inventes datos que no estén en el material.

Reglas de fondos:
- {limite}
- {"Incluí un motivo de una oración por cada fondo." if explica else "motivo: una oración corta, solo si proponés un fondo nuevo."}
- Usá solo fondos de la lista. No inventes fondos.
- El número de id va solo en el campo id del JSON. No lo escribas en texto ni en motivo. Llamá a cada fondo por su título.
- Si hacés una lista, poné cada ítem en su propio renglón, empezando con un guión.

Proyecto:
{resumen}

Fragmentos del proyecto:
{proyecto}

Fondos:
{fichas}

Fragmentos de las bases:
{extractos or "Sin fragmentos."}

Conversación:
{historial or "Es la primera pregunta."}

Pregunta:
{pregunta}
"""
    try:
        mensaje = llm_breve.invoke(prompt)
    except Exception as error:
        raise RelacionarError("No se pudo consultar a Qwen.") from error

    crudo = getattr(mensaje, "content", None) or ""
    datos = _leer_json(crudo)
    texto = _acortar(_extraer_texto(crudo, datos), explica)
    if not texto:
        raise RelacionarError("Qwen no devolvió una respuesta.")

    if len(fondos) == 1:
        texto = _corregir_fechas(texto, fondos[0], citados)

    if explica:
        return texto, _tarjetas_explicadas(fondos, datos.get("fondos"))

    if seguir_hilo or nombrados:
        if len(fondos) == 1:
            return texto, [_tarjeta(fondos[0])]
        return texto, []

    pedidos = datos.get("fondos")
    return texto, _tarjetas(fondos, pedidos if isinstance(pedidos, list) else [], not isinstance(pedidos, list))
