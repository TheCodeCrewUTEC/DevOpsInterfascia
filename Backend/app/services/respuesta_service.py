import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

from app.services.documento_uy import instruccion_formato, instruccion_nombre, limpiar_respuesta_nombre

load_dotenv()

# ============================================================
# CONFIGURACIÓN
# ============================================================

MODEL_NAME = "qwen2.5:3b-instruct"
# Vacío: Ollama en esta misma máquina. Con URL, el servidor usa el Ollama de otra PC.
OLLAMA_URL = os.getenv("OLLAMA_URL") or None

# Mismo num_ctx que qwen_service: si cambia, Ollama recarga el modelo entre etapas
NUM_CTX = 8192
# Sin tope, un campo abierto ("Información sobre el Proyecto Postulado") hace que
# el modelo redacte hasta llenar el contexto. La llamada es síncrona y el worker
# no sigue hasta que termina. 512 tokens alcanzan para un JSON breve.
NUM_PREDICT = 512

llm = ChatOllama(
    model=MODEL_NAME,
    temperature=0,
    num_ctx=NUM_CTX,
    num_predict=NUM_PREDICT,
    base_url=OLLAMA_URL,
    client_kwargs={"timeout": 120},
)

# Hasta este tamaño se manda el documento completo en cada campo (~3 caracteres por
# token, dejando lugar a las instrucciones y a la respuesta dentro de NUM_CTX).
MAX_CARACTERES_DOCUMENTO_COMPLETO = 18000


def cabe_documento_completo(chunks: list[dict[str, Any]]) -> bool:
    """Con documentos chicos conviene mandar todos los chunks en cada campo.

    El prompt queda igual hasta el nombre del campo, así Ollama reutiliza lo ya
    procesado (caché del prefijo) y cada campo tarda segundos en vez de minutos en CPU.
    """
    return 0 < sum(len(c.get("texto", "")) for c in chunks) <= MAX_CARACTERES_DOCUMENTO_COMPLETO


# ============================================================
# CONSTRUIR CONTEXTO
# ============================================================

def construir_contexto(
    chunks_relevantes: list[dict[str, Any]]
) -> str:

    context_parts = []

    for indice, chunk in enumerate(
        chunks_relevantes,
        start=1
    ):

        texto = chunk.get("texto", "")
        documento = chunk.get("documento", "")
        pagina = chunk.get("pagina")

        # La similitud cambia en cada campo: incluirla rompería la caché del prefijo
        context_parts.append(
            f"""
FUENTE - Chunk {indice}
Documento: {documento}
Página: {pagina}

{texto}
"""
        )

    return "\n".join(context_parts)


# ============================================================
# RESPUESTA CORTA
# ============================================================

def _primeras_oraciones(texto: str, cantidad: int = 2) -> str:
    texto = " ".join(texto.split())
    if len(texto) <= 400:
        return texto

    partes = re.split(r"(?<=[.!?])\s+", texto)
    tomadas = [parte for parte in partes if parte][:cantidad]
    return " ".join(tomadas) if tomadas else texto[:400]


def _texto_de_respuesta(content: str) -> str | None:
    """Saca el texto aunque el JSON haya quedado cortado por el tope de tokens."""

    marca = re.search(r'"respuesta"\s*:\s*"', content)
    if not marca:
        return None

    chars: list[str] = []
    escaped = False

    for ch in content[marca.end():]:
        if escaped:
            chars.append(" " if ch in "nt" else ch)
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"':
            break
        chars.append(ch)

    texto = "".join(chars).strip()
    if not texto or texto.lower() == "null":
        return None

    return _primeras_oraciones(texto)


# ============================================================
# GENERAR RESPUESTA CON QWEN
# ============================================================

def _describir_columnas(columnas: list[dict[str, Any]]) -> str:
    lineas = []
    for columna in columnas:
        etiqueta = " ".join(str(columna.get("etiqueta") or "").replace("*", " ").split())
        if not etiqueta:
            continue
        opciones = [str(opcion).strip() for opcion in (columna.get("opciones") or []) if str(opcion).strip()]
        formato = instruccion_formato(etiqueta)
        nombre = instruccion_nombre(etiqueta)
        if opciones and len(opciones) <= 12:
            lineas.append(f"- {etiqueta}. Opciones: {'; '.join(opciones)}")
        elif columna.get("depende_de"):
            lineas.append(f"- {etiqueta}. Tiene que corresponder a la columna de la que depende, en la misma fila.")
        elif formato:
            lineas.append(f"- {etiqueta}. {formato}")
        elif nombre:
            lineas.append(f"- {etiqueta}. {nombre}")
        else:
            lineas.append(f"- {etiqueta}")
    return "\n".join(lineas)


def generar_respuesta(
    campo: str,
    tipo: str,
    chunks_relevantes: list[dict[str, Any]],
    opciones: list[str] | None = None,
    columnas: list[dict[str, Any]] | None = None,
    detalle: str | None = None,
    seccion: str | None = None,
) -> dict[str, Any]:

    # --------------------------------------------------------
    # Sin información
    # --------------------------------------------------------

    if not chunks_relevantes:

        return {
            "respuesta": None,
            "fuentes": []
        }

    # --------------------------------------------------------
    # Construir contexto
    # --------------------------------------------------------

    contexto = construir_contexto(
        chunks_relevantes
    )

    # --------------------------------------------------------
    # Prompt
    # --------------------------------------------------------

    # Orden pensado para la caché de Ollama: todo lo que se repite entre campos va
    # primero y el campo va al final. Las opciones son de este campo, van al final.
    lista = [opcion.strip() for opcion in (opciones or []) if str(opcion).strip()]
    texto_seccion = " ".join(str(seccion or "").split())
    texto_detalle = " ".join(str(detalle or "").split())
    formato = instruccion_formato(campo)
    texto_nombre = instruccion_nombre(campo)
    descripcion_columnas = _describir_columnas(columnas or [])
    bloque_opciones = ""
    if descripcion_columnas:
        bloque_opciones = f"""
Este campo es una tabla. Cada persona o registro es una fila.
Devolvé "respuesta" como una lista de objetos, uno por fila, con estas columnas.
Copiá los nombres de columna tal cual. No inventes filas.
Si los documentos no identifican ningún registro, devolvé [].

Columnas:
{descripcion_columnas}
"""
    elif lista:
        lineas = "\n".join(f"- {opcion}" for opcion in lista)
        bloque_opciones = f"""
Este campo es una lista. La respuesta debe ser exactamente una de estas opciones,
copiada tal cual, o null si ninguna está respaldada por los documentos.
No redactes una oración ni inventes una opción que no figure aquí.

Opciones:
{lineas}
"""
    if descripcion_columnas:
        cierre = "La respuesta es la lista de filas, nada más."
    elif lista:
        cierre = "La respuesta es una opción de la lista, nada más."
    elif formato:
        cierre = "La respuesta es el número, nada más."
    elif texto_nombre:
        cierre = "La respuesta es el nombre, nada más."
    else:
        cierre = "La respuesta es una o dos oraciones, nada más."
    bloque_ubicacion = ""
    if texto_seccion or texto_detalle:
        lineas_ubicacion = []
        if texto_seccion:
            lineas_ubicacion.append(f"Sección: {texto_seccion}")
        if texto_detalle:
            lineas_ubicacion.append(f"Subtítulo: {texto_detalle}")
        lineas_ubicacion.append(
            "La sección y el subtítulo dicen de quién es el dato. "
            "Lo que tenés que devolver es lo que pide el nombre del campo, "
            "no un número que aparezca en el subtítulo."
        )
        bloque_ubicacion = "\n" + "\n".join(lineas_ubicacion) + "\n"
    prompt = f"""
Eres un asistente que completa formularios de postulación
utilizando exclusivamente la información proporcionada en
los documentos de un proyecto.

Reglas:

1. Utiliza exclusivamente la información proporcionada.

2. No inventes información.

3. No completes información utilizando conocimiento externo.

4. Si la información necesaria no aparece claramente,
   responde null.

5. Si el campo pide un texto, responde en una o dos
   oraciones. No redactes un informe ni copies párrafos
   del documento. Si pide un nombre o una razón social,
   responde solo ese nombre, nunca un RUT ni otro número.
   Si pide un RUT, una cédula, un número de documento,
   una fecha, un correo o un teléfono, responde solo ese dato.

6. Mantén los datos exactamente como aparecen cuando se
   trate de identificadores, nombres, números, fechas,
   correos o teléfonos.

7. Las fuentes deben corresponder únicamente a los chunks
   que realmente utilizaste para construir la respuesta.

8. No expliques tu razonamiento.

9. No agregues información que no esté respaldada por
   los documentos.

10. Si más abajo hay una lista de opciones, la respuesta es
    exactamente una de esas opciones, copiada tal cual, o null.
    En ese caso no redactes una oración.

Devuelve únicamente JSON válido con esta estructura:

{{
    "respuesta": "...",
    "fuentes": [
        {{
            "chunk": 1
        }}
    ]
}}

Si no existe información suficiente:

{{
    "respuesta": null,
    "fuentes": []
}}

Información de los documentos:

{contexto}

Campo del formulario:
{campo}
{bloque_ubicacion}{f"\n{formato}\n" if formato else ""}{f"\n{texto_nombre}\n" if texto_nombre else ""}
Tipo de campo:
{tipo}
{bloque_opciones}
Cerrá el JSON. {cierre}
"""

    # --------------------------------------------------------
    # Consultar Qwen
    # --------------------------------------------------------

    print("=" * 60)
    print("[QWEN] Generando respuesta")
    print(f"[QWEN] Campo: {campo}")
    print(f"[QWEN] Tipo: {tipo}")

    response = llm.invoke(prompt)

    content = response.content

    if content is None:
        return {
            "respuesta": None,
            "fuentes": []
        }

    content = str(content).strip()

    print(f"[QWEN] Respuesta RAW:")
    print(content)

    # --------------------------------------------------------
    # Intentar interpretar JSON
    # --------------------------------------------------------

    try:

        resultado = json.loads(content)

    except json.JSONDecodeError:

        print("[QWEN] ⚠ No devolvió JSON válido")
        respuesta = _texto_de_respuesta(content)

        return {
            "respuesta": respuesta,
            "fuentes": []
        }

    # --------------------------------------------------------
    # Validar estructura
    # --------------------------------------------------------

    if not isinstance(resultado, dict):

        print("[QWEN] ⚠ La respuesta no es un objeto JSON")

        return {
            "respuesta": None,
            "fuentes": []
        }

    respuesta = resultado.get(
        "respuesta"
    )

    if isinstance(respuesta, str) and not descripcion_columnas and not formato and not texto_nombre:
        respuesta = _primeras_oraciones(respuesta)

    respuesta = limpiar_respuesta_nombre(campo, respuesta)

    fuentes = resultado.get(
        "fuentes",
        []
    )

    if not isinstance(fuentes, list):
        fuentes = []

    # --------------------------------------------------------
    # Normalizar fuentes
    # --------------------------------------------------------

    fuentes_validas = []

    for fuente in fuentes:

        if not isinstance(fuente, dict):
            continue

        chunk = fuente.get("chunk", fuente.get("chunk_id"))

        if chunk is None:
            continue

        fuentes_validas.append({
            "chunk": chunk
        })

    # --------------------------------------------------------
    # Resultado final
    # --------------------------------------------------------

    resultado_final = {
        "respuesta": respuesta,
        "fuentes": fuentes_validas
    }

    print(
        f"[QWEN] Respuesta final: "
        f"{resultado_final['respuesta']}"
    )

    print(
        f"[QWEN] Fuentes utilizadas: "
        f"{resultado_final['fuentes']}"
    )

    return resultado_final