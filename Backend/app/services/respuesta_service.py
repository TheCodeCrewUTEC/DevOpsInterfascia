import json
import os
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

llm = ChatOllama(
    model=MODEL_NAME,
    temperature=0,
    num_ctx=4096,
    base_url=OLLAMA_URL,
)


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
        similitud = chunk.get("similitud", 0)
        documento = chunk.get("documento", "")
        pagina = chunk.get("pagina")

        context_parts.append(
            f"""
FUENTE - Chunk {indice}
Documento: {documento}
Página: {pagina}
Similitud: {similitud:.4f}

{texto}
"""
        )

    return "\n".join(context_parts)


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

    prompt = f"""
Eres un asistente que completa formularios de postulación
utilizando exclusivamente la información proporcionada en
los documentos de un proyecto.

Campo del formulario:
{campo}

Tipo de campo:
{tipo}

Información recuperada de los documentos:

{contexto}

Reglas:

1. Utiliza exclusivamente la información proporcionada.

2. No inventes información.

3. No completes información utilizando conocimiento externo.

4. Si la información necesaria no aparece claramente,
   responde null.

5. Si existe información suficiente, responde de forma
   breve y directa.

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

        return {
            "respuesta": None,
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