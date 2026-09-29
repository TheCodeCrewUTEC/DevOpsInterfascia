import json

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate


# CONFIGURACIÓN
OLLAMA_MODEL = "qwen2.5:3b-instruct"

llm = ChatOllama(
    model=OLLAMA_MODEL,
    temperature=0,
)

# PROMPT
PROMPT_EXTRAER_CAMPOS = """
Tu tarea es analizar un formulario de postulación.

Debes identificar TODOS los campos que el usuario debe completar
en el formulario.

NO debes responder los campos.
NO debes inventar información.
NO debes completar valores.
NO debes resumir el formulario.

Solamente debes identificar los campos solicitados.

Para cada campo devuelve:

- nombre: nombre del campo
- tipo: tipo de dato esperado
- descripcion: qué información solicita el campo

Tipos permitidos:

- texto
- texto_largo
- numero
- fecha
- seleccion
- multiple
- tabla
- otro

Devuelve EXCLUSIVAMENTE JSON válido con esta estructura:

{{
    "campos": [
        {{
            "nombre": "...",
            "tipo": "...",
            "descripcion": "..."
        }}
    ]
}}

FORMULARIO:

{formulario}
"""


prompt = ChatPromptTemplate.from_template(
    PROMPT_EXTRAER_CAMPOS
)

# EXTRAER CAMPOS
def extraer_campos_formulario(texto: str) -> dict:

    print(
        "[QWEN] Analizando formulario..."
    )

    mensajes = prompt.format_messages(
        formulario=texto
    )

    respuesta = llm.invoke(
        mensajes
    )

    contenido = respuesta.content

    print(
        "[QWEN] Respuesta recibida"
    )

    print(
        contenido
    )

    # PARSEAR JSON
    try:

        resultado = json.loads(
            contenido
        )

    except json.JSONDecodeError:

        print(
            "[QWEN] La respuesta no es JSON válido"
        )

        raise Exception(
            "Qwen no devolvió un JSON válido"
        )

    return resultado