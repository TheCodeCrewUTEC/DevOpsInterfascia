import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

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

def generar_respuesta(
    campo: str,
    tipo: str,
    chunks_relevantes: list[dict[str, Any]],
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
    # primero y el campo va al final.
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

5. Si existe información suficiente, responde en una o
   dos oraciones. No redactes un informe ni copies
   párrafos del documento.

6. Mantén los datos exactamente como aparecen cuando se
   trate de identificadores, nombres, números, fechas,
   correos o teléfonos.

7. Las fuentes deben corresponder únicamente a los chunks
   que realmente utilizaste para construir la respuesta.

8. No expliques tu razonamiento.

9. No agregues información que no esté respaldada por
   los documentos.

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

Tipo de campo:
{tipo}

Cerrá el JSON. La respuesta es una o dos oraciones, nada más.
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

    if isinstance(respuesta, str):
        respuesta = _primeras_oraciones(respuesta)

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