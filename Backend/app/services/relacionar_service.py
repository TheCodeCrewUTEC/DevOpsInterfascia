import json
import os
import re
import threading

from langchain_ollama import ChatOllama

from app.database.connection import get_connection

EMBED_MODEL = "intfloat/multilingual-e5-small"
MODEL_NAME = "qwen2.5:3b-instruct"
OLLAMA_URL = os.getenv("OLLAMA_URL") or None

_trabajo = threading.Lock()
_modelo = None
_perfiles: list[dict] | None = None
_convocatorias: list[dict] | None = None

llm = ChatOllama(
    model=MODEL_NAME,
    temperature=0,
    num_ctx=8192,
    num_predict=2000,
    base_url=OLLAMA_URL,
)


class RelacionarError(Exception):
    pass


def recomendar(descripcion: str) -> dict:
    with _trabajo:
        return _recomendar(descripcion.strip())


def _modelo_embedding():
    global _modelo
    if _modelo is None:
        from sentence_transformers import SentenceTransformer

        _modelo = SentenceTransformer(EMBED_MODEL)
    return _modelo


def _similitud(consulta, documento) -> float:
    return float(sum(a * b for a, b in zip(consulta, documento)))


def _recortar(valor, limite: int) -> str:
    texto = re.sub(r"\s+", " ", (valor or "").strip())
    if len(texto) <= limite:
        return texto
    return texto[: limite - 1].rstrip() + "…"


def _fecha(valor) -> str | None:
    if valor is None:
        return None
    return str(valor)[:10]


def _lineas(texto: str | None, limite: int = 6) -> list[str]:
    lineas = []
    for linea in (texto or "").splitlines():
        limpia = re.sub(r"\s+", " ", linea).strip(" -•\t")
        if len(limpia) < 12:
            continue
        lineas.append(limpia[:180])
        if len(lineas) >= limite:
            break
    return lineas


def _abierta(estado: str | None) -> bool:
    return (estado or "").strip().casefold() == "abierta"


def _catalogo_convocatorias() -> list[dict]:
    global _convocatorias
    if _convocatorias is not None:
        return _convocatorias

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
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
                    financiamiento
                FROM convocatoria
                WHERE descripcion IS NOT NULL
                  AND btrim(descripcion) <> ''
                  AND (fecha_apertura IS NOT NULL OR fecha_cierre IS NOT NULL)
                """
            )
            filas = cur.fetchall()
    finally:
        conn.close()

    fondos = []
    textos = []
    for fila in filas:
        texto = " ".join(
            parte
            for parte in (fila[1], fila[6], fila[7], fila[8])
            if parte and str(parte).strip()
        )
        fondos.append({
            "id": fila[0],
            "titulo": fila[1],
            "institucion": fila[2],
            "estado": fila[3],
            "fecha_apertura": _fecha(fila[4]),
            "fecha_cierre": _fecha(fila[5]),
            "descripcion": fila[6],
            "beneficiarios": fila[7],
            "requisitos": fila[8],
            "financiamiento": None if fila[9] is None else str(fila[9]),
        })
        textos.append("passage: " + _recortar(texto, 900))

    if textos:
        vectores = _modelo_embedding().encode(
            textos,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False,
        )
        for fondo, vector in zip(fondos, vectores):
            fondo["vector"] = vector

    _convocatorias = fondos
    return _convocatorias


def _fondos_cercanos(consulta_vector) -> list[dict]:
    ordenados = sorted(
        _catalogo_convocatorias(),
        key=lambda fondo: _similitud(consulta_vector, fondo["vector"]),
        reverse=True,
    )
    # Solo entran las más parecidas. Así una convocatoria abierta de otro tema
    # no ocupa el lugar de un fondo que sí encaja.
    mas_parecidas = ordenados[:12]
    abiertas = [fondo for fondo in mas_parecidas if _abierta(fondo["estado"])]
    if not abiertas:
        abiertas = [fondo for fondo in ordenados if _abierta(fondo["estado"])][:3]
    cerradas = [fondo for fondo in mas_parecidas if not _abierta(fondo["estado"])][:3]
    elegidos = []
    vistos = set()
    for fondo in abiertas + cerradas:
        if fondo["id"] in vistos:
            continue
        vistos.add(fondo["id"])
        elegidos.append(fondo)
    return elegidos


def _perfiles_investigadores() -> list[dict]:
    global _perfiles
    if _perfiles is not None:
        return _perfiles

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    nombre,
                    apellido,
                    institucion,
                    titulo,
                    investigaciones,
                    nivel_sni,
                    categoria_sni
                FROM investigadores
                """
            )
            filas = cur.fetchall()
    finally:
        conn.close()

    textos = []
    perfiles = []
    for fila in filas:
        investigaciones = fila[5] or ""
        if not investigaciones.strip() and not (fila[4] or "").strip():
            continue
        texto = " ".join(
            parte
            for parte in (
                fila[1],
                fila[2],
                fila[3],
                fila[4],
                _recortar(investigaciones, 700),
            )
            if parte and str(parte).strip()
        )
        perfiles.append({
            "id": fila[0],
            "nombre": fila[1],
            "apellido": fila[2],
            "institucion": fila[3],
            "titulo": fila[4],
            "investigaciones": investigaciones,
            "nivel_sni": fila[6],
            "categoria_sni": fila[7],
            "proyectos": _lineas(investigaciones),
        })
        textos.append("passage: " + texto)

    if not textos:
        _perfiles = []
        return _perfiles

    vectores = _modelo_embedding().encode(
        textos,
        normalize_embeddings=True,
        batch_size=32,
        show_progress_bar=False,
    )
    for perfil, vector in zip(perfiles, vectores):
        perfil["vector"] = vector
    _perfiles = perfiles
    return _perfiles


def _investigadores_cercanos(consulta_vector, limite: int = 6) -> list[dict]:
    ordenados = sorted(
        _perfiles_investigadores(),
        key=lambda perfil: _similitud(consulta_vector, perfil["vector"]),
        reverse=True,
    )
    return ordenados[:limite]


def _proyectos_registrados(consulta_vector) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, nombre, estado, anio, descripcion, investigadores
                FROM proyectos
                WHERE nombre IS NOT NULL AND btrim(nombre) <> ''
                """
            )
            filas = cur.fetchall()
    finally:
        conn.close()

    if not filas:
        return []

    textos = []
    proyectos = []
    for fila in filas:
        texto = " ".join(
            parte for parte in (fila[1], fila[3], fila[4], fila[5]) if parte and str(parte).strip()
        )
        proyectos.append({
            "id": fila[0],
            "nombre": fila[1],
            "anio": fila[3],
            "descripcion": fila[4],
            "investigador": fila[5],
        })
        textos.append("passage: " + _recortar(texto, 700))

    vectores = _modelo_embedding().encode(
        textos,
        normalize_embeddings=True,
        batch_size=32,
        show_progress_bar=False,
    )
    ordenados = sorted(
        zip(proyectos, vectores),
        key=lambda par: _similitud(consulta_vector, par[1]),
        reverse=True,
    )
    return [proyecto for proyecto, _vector in ordenados[:5]]


def _bloque_fondos(fondos: list[dict]) -> str:
    partes = []
    for fondo in fondos:
        partes.append(
            "\n".join([
                f"[id={fondo['id']}] {fondo['estado'] or 'Sin estado'} | {fondo['titulo']}",
                f"Cierre: {fondo['fecha_cierre'] or 'sin fecha'}",
                _recortar(fondo["descripcion"], 420),
            ])
        )
    return "\n\n".join(partes)


def _bloque_personas(personas: list[dict]) -> str:
    partes = []
    for persona in personas:
        nombre = " ".join(
            parte for parte in (persona["nombre"], persona["apellido"]) if parte and parte.strip()
        )
        proyectos = "\n".join(f"- {linea}" for linea in persona["proyectos"][:5]) or "- Sin proyectos listados"
        partes.append(
            "\n".join([
                f"[id={persona['id']}] {nombre}",
                persona["institucion"] or "Sin institución",
                persona["titulo"] or "Sin título",
                "Proyectos:",
                proyectos,
            ])
        )
    return "\n\n".join(partes)


def _bloque_registros(proyectos: list[dict]) -> str:
    if not proyectos:
        return "No hay proyectos cargados en la tabla de proyectos."
    partes = []
    for proyecto in proyectos:
        partes.append(
            "\n".join([
                f"[id={proyecto['id']}] {proyecto['nombre']} ({proyecto['anio'] or 'sin año'})",
                _recortar(proyecto.get("descripcion"), 300),
            ])
        )
    return "\n\n".join(partes)


def _preguntar(descripcion: str, fondos, personas, registros) -> dict:
    prompt = f"""
Sos el consultor de Interfascia. Recomendás usando solamente los candidatos de la base.

Proyecto de la persona:
{_recortar(descripcion, 8000)}

Fondos candidatos:
{_bloque_fondos(fondos)}

Investigadores candidatos:
{_bloque_personas(personas)}

Proyectos financiados registrados:
{_bloque_registros(registros)}

Elegí:
- hasta 5 fondos a los que podría postularse, priorizando estado Abierta si encajan con el proyecto
- hasta 5 investigadores que podrían ser de utilidad
- hasta 5 proyectos anteriores similares. Si hay proyectos registrados, usá su id. Si no, copiá una línea de "Proyectos" de un investigador candidato.

No inventes ids ni nombres que no estén en los candidatos.
No incluyas un candidato si no tiene una relación clara con el proyecto.
El resumen solo puede nombrar fondos, personas o proyectos que también estén en el JSON.
El motivo es una sola oración en español y tiene que decir por qué se parece al proyecto.

Devolvé únicamente este JSON:
{{
  "resumen": "dos oraciones",
  "fondos": [{{"id": 1, "motivo": "..."}}],
  "investigadores": [{{"id": 1, "motivo": "..."}}],
  "proyectos": [{{"id": null, "investigador_id": 1, "nombre": "línea copiada", "motivo": "..."}}]
}}
"""
    try:
        respuesta = llm.invoke(prompt)
    except Exception as error:
        raise RelacionarError("No se pudo consultar a Qwen.") from error

    contenido = getattr(respuesta, "content", None)
    if not contenido:
        return {}
    return _leer_json(str(contenido))


def _leer_json(texto: str) -> dict:
    limpio = re.sub(r"```(?:json)?", "", texto, flags=re.IGNORECASE)
    inicio = limpio.find("{")
    fin = limpio.rfind("}")
    if inicio < 0 or fin <= inicio:
        return {}
    fragmento = re.sub(r",\s*([}\]])", r"\1", limpio[inicio:fin + 1])
    try:
        datos = json.loads(fragmento)
    except json.JSONDecodeError:
        return {}
    if not isinstance(datos, dict):
        return {}
    return datos


def _motivo(valor, respaldo: str) -> str:
    texto = str(valor or "").strip()
    return texto or respaldo


def _armar(datos: dict, fondos: list[dict], personas: list[dict], registros: list[dict]) -> dict:
    fondos_por_id = {fondo["id"]: fondo for fondo in fondos}
    personas_por_id = {persona["id"]: persona for persona in personas}
    registros_por_id = {proyecto["id"]: proyecto for proyecto in registros}

    fondos_ok = []
    for item in datos.get("fondos") or []:
        if not isinstance(item, dict):
            continue
        fondo = fondos_por_id.get(item.get("id"))
        if fondo is None or any(actual["id"] == fondo["id"] for actual in fondos_ok):
            continue
        fondos_ok.append({**_publico_fondo(fondo), "motivo": _motivo(item.get("motivo"), "Se acerca al tema de tu proyecto.")})
        if len(fondos_ok) == 5:
            break

    personas_ok = []
    for item in datos.get("investigadores") or []:
        if not isinstance(item, dict):
            continue
        persona = personas_por_id.get(item.get("id"))
        if persona is None or any(actual["id"] == persona["id"] for actual in personas_ok):
            continue
        personas_ok.append({
            **_publico_persona(persona),
            "motivo": _motivo(item.get("motivo"), "Su trayectoria se acerca al tema de tu proyecto."),
        })
        if len(personas_ok) == 5:
            break

    proyectos_ok = []
    for item in datos.get("proyectos") or []:
        if not isinstance(item, dict):
            continue
        armado = _proyecto_valido(item, personas_por_id, registros_por_id)
        if armado is None:
            continue
        if any(actual["nombre"].casefold() == armado["nombre"].casefold() for actual in proyectos_ok):
            continue
        proyectos_ok.append(armado)
        if len(proyectos_ok) == 5:
            break

    if not fondos_ok:
        fondos_ok = [
            {**_publico_fondo(fondo), "motivo": "Es de los fondos más cercanos al tema que describiste."}
            for fondo in fondos[:5]
        ]
    if not personas_ok:
        personas_ok = [
            {**_publico_persona(persona), "motivo": "Su trabajo se acerca al tema que describiste."}
            for persona in personas[:5]
        ]
    if not proyectos_ok:
        proyectos_ok = _proyectos_de_respaldo(personas, registros)

    resumen = str(datos.get("resumen") or "").strip()
    if not resumen:
        resumen = "Estas son las coincidencias más cercanas que encontré en la base para el proyecto que describiste."

    fondos_ok.sort(key=lambda fondo: not _abierta(fondo["estado"]))

    return {
        "resumen": resumen,
        "fondos": fondos_ok,
        "investigadores": personas_ok,
        "proyectos": proyectos_ok,
    }


def _publico_fondo(fondo: dict) -> dict:
    return {
        "id": fondo["id"],
        "titulo": fondo["titulo"],
        "institucion": fondo["institucion"],
        "estado": fondo["estado"],
        "fecha_apertura": fondo["fecha_apertura"],
        "fecha_cierre": fondo["fecha_cierre"],
        "descripcion": fondo["descripcion"],
        "financiamiento": fondo["financiamiento"],
    }


def _publico_persona(persona: dict) -> dict:
    return {
        "id": persona["id"],
        "nombre": persona["nombre"],
        "apellido": persona["apellido"],
        "institucion": persona["institucion"],
        "titulo": persona["titulo"],
        "investigaciones": persona["investigaciones"],
        "nivel_sni": persona["nivel_sni"],
        "categoria_sni": persona["categoria_sni"],
    }


def _proyecto_valido(item: dict, personas_por_id: dict, registros_por_id: dict) -> dict | None:
    motivo = _motivo(item.get("motivo"), "Se parece al proyecto que describiste.")
    registro_id = item.get("id")
    if isinstance(registro_id, int) and registro_id in registros_por_id:
        registro = registros_por_id[registro_id]
        return {
            "nombre": registro["nombre"],
            "anio": registro["anio"],
            "descripcion": registro["descripcion"],
            "investigador_id": None,
            "investigador": registro["investigador"],
            "motivo": motivo,
        }

    investigador_id = item.get("investigador_id")
    persona = personas_por_id.get(investigador_id)
    nombre = re.sub(r"\s+", " ", str(item.get("nombre") or "")).strip()
    if persona is None or len(nombre) < 12:
        return None
    linea = _linea_conocida(nombre, persona["proyectos"])
    if linea is None:
        return None
    investigador = " ".join(
        parte for parte in (persona["nombre"], persona["apellido"]) if parte and str(parte).strip()
    )
    return {
        "nombre": linea,
        "anio": None,
        "descripcion": None,
        "investigador_id": persona["id"],
        "investigador": investigador or None,
        "motivo": motivo,
    }


def _linea_conocida(nombre: str, lineas: list[str]) -> str | None:
    buscada = nombre.casefold()
    for linea in lineas:
        actual = linea.casefold()
        if buscada in actual or actual in buscada:
            return linea
    return None


def _proyectos_de_respaldo(personas: list[dict], registros: list[dict]) -> list[dict]:
    if registros:
        return [
            {
                "nombre": proyecto["nombre"],
                "anio": proyecto["anio"],
                "descripcion": proyecto["descripcion"],
                "investigador_id": None,
                "investigador": proyecto["investigador"],
                "motivo": "Es de los proyectos registrados más cercanos a tu descripción.",
            }
            for proyecto in registros[:5]
        ]

    proyectos = []
    for persona in personas:
        if not persona["proyectos"]:
            continue
        investigador = " ".join(
            parte for parte in (persona["nombre"], persona["apellido"]) if parte and str(parte).strip()
        )
        proyectos.append({
            "nombre": persona["proyectos"][0],
            "anio": None,
            "descripcion": None,
            "investigador_id": persona["id"],
            "investigador": investigador or None,
            "motivo": "Forma parte de la trayectoria más cercana al tema que describiste.",
        })
        if len(proyectos) == 5:
            break
    return proyectos


def _recomendar(descripcion: str) -> dict:
    try:
        consulta = _modelo_embedding().encode(
            "query: " + descripcion,
            normalize_embeddings=True,
        )
        fondos = _fondos_cercanos(consulta)
        personas = _investigadores_cercanos(consulta)
        registros = _proyectos_registrados(consulta)
    except RelacionarError:
        raise
    except Exception as error:
        raise RelacionarError("No se pudo consultar la base de conocimiento.") from error

    if not fondos and not personas and not registros:
        raise RelacionarError("La base no tiene información suficiente para recomendar.")

    datos = _preguntar(descripcion, fondos, personas, registros)
    return _armar(datos, fondos, personas, registros)
