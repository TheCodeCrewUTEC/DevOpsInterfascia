from pathlib import Path
import json
import re
import time

from docling.document_converter import DocumentConverter
from langchain_ollama import ChatOllama


# ============================================================
# CONFIGURACIÓN
# ============================================================

MODEL_NAME = "qwen2.5:3b-instruct"


llm = ChatOllama(
    model=MODEL_NAME,
    temperature=0,
    num_ctx=4096,
)

# ============================================================
# PROMPT
# ============================================================

def preguntar_qwen(texto_pagina):

    prompt = f"""
Analiza el siguiente texto extraído de una página de un formulario de postulación.

Tu tarea es identificar TODOS los campos que requieren una acción, dato,
selección, respuesta o confirmación por parte del usuario.

IMPORTANTE:
Un campo puede ser muy corto. No descartes un campo solamente porque tenga
una o dos palabras.

Por ejemplo, estos SÍ son campos válidos:

- Nombre
- Apellido
- Género
- RUT
- Departamento
- Localidad
- Teléfono
- E-mail
- Mujeres
- Hombres
- Personal total
- Personal ocupado
- Razón Social
- CIIU Sección
- Tipo de documento
- Tamaño de la empresa

También son campos válidos las preguntas completas que requieren que el
postulante escriba una respuesta.

==================================================
QUÉ DEBES INCLUIR
==================================================

Incluye:

1. Campos donde el usuario debe escribir texto.

2. Campos donde debe ingresar números, cantidades o identificadores.

3. Campos donde debe ingresar una fecha.

4. Campos donde debe ingresar un correo electrónico.

5. Campos donde debe seleccionar una opción, categoría o valor de una lista.

6. Campos donde debe marcar una casilla para aceptar, confirmar o declarar algo.

7. Preguntas que requieren una respuesta del usuario.

8. Campos cortos que representen claramente un dato que el usuario debe
   proporcionar.

==================================================
CLASIFICACIÓN DE TIPOS
==================================================

Cada campo DEBE tener uno de estos tipos:

- "text"
- "numero"
- "fecha"
- "email"
- "seleccion"
- "checkbox"
- "pregunta"

--------------------------------------------------
TIPO: numero
--------------------------------------------------

Utiliza "numero" para:

- cantidades
- conteos
- números de documento
- identificadores numéricos
- cantidades de personas
- cantidades de empleados

Ejemplos:

- RUT → numero
- Número de documento → numero
- Mujeres → numero
- Hombres → numero
- Personal total → numero
- Personal ocupado → numero
- Cantidad de empleados → numero

--------------------------------------------------
TIPO: seleccion
--------------------------------------------------

Utiliza "seleccion" SOLAMENTE cuando el usuario debe elegir una opción,
categoría o valor de una lista.

Ejemplos:

- Género → seleccion
- Tipo de documento → seleccion
- Tamaño de la empresa → seleccion
- Naturaleza Jurídica → seleccion, si presenta opciones
- Departamento → seleccion, si presenta opciones
- País de documento → seleccion, si presenta opciones

No utilices "seleccion" simplemente porque un campo puede tener diferentes
respuestas posibles.

--------------------------------------------------
TIPO: text
--------------------------------------------------

Utiliza "text" para información textual que el usuario debe ingresar.

Ejemplos:

- Nombre → text
- Apellido → text
- Razón Social → text
- Dirección fiscal → text
- Localidad → text
- Nombre de la empresa → text
- Teléfono de contacto → text
- Persona Responsable por la Ejecución → text

--------------------------------------------------
TIPO: fecha
--------------------------------------------------

Utiliza "fecha" para campos donde el usuario debe ingresar una fecha.

Ejemplos:

- Fecha de inicio de actividades
- Fecha de nacimiento
- Fecha de cierre

--------------------------------------------------
TIPO: email
--------------------------------------------------

Utiliza "email" para campos donde el usuario debe ingresar un correo
electrónico.

Ejemplos:

- E-mail
- E-mail de contacto
- Correo electrónico

--------------------------------------------------
TIPO: checkbox
--------------------------------------------------

Utiliza "checkbox" cuando exista una acción explícita de marcar, aceptar,
confirmar o declarar mediante una casilla.

Ejemplos:

- Consentimiento de datos
- Consentimiento de tratamiento de datos
- Acepto los términos
- Declaro no tener incompatibilidades

NO conviertas automáticamente cualquier texto legal en un checkbox.

Debe existir una acción explícita de aceptación, confirmación o declaración.

--------------------------------------------------
TIPO: pregunta
--------------------------------------------------

Utiliza "pregunta" cuando el campo está formulado como una pregunta y
requiere que el usuario escriba una respuesta, explicación o descripción.

Ejemplos:

- ¿En qué programa participó?
- ¿En qué convocatoria participó?
- ¿En qué etapa se encuentra la empresa?
- ¿En qué situación se encuentra la empresa actualmente?
- ¿La empresa tiene potencial de crecimiento?
- ¿Cuáles son los principales problemas o desafíos?

NO utilices "text" para preguntas abiertas.

Si una pregunta requiere una respuesta desarrollada por parte del usuario,
debe utilizarse "pregunta".

==================================================
REGLAS IMPORTANTES DE CLASIFICACIÓN
==================================================

REGLA 1:
TODOS los objetos de la respuesta DEBEN contener exactamente estas dos
propiedades:

"campo"
"tipo"

Nunca devuelvas un objeto que solamente tenga "campo".

INCORRECTO:

{{
  "campo": "Mujeres"
}}

CORRECTO:

{{
  "campo": "Mujeres",
  "tipo": "numero"
}}

--------------------------------------------------

REGLA 2:
Los campos cortos son válidos.

No descartes campos solamente por ser palabras o frases cortas.

Estos pueden ser campos válidos:

- Nombre
- Apellido
- Género
- RUT
- Mujeres
- Hombres
- Personal total
- Departamento
- Localidad
- E-mail

--------------------------------------------------

REGLA 3:
No conviertas explicaciones, definiciones o aclaraciones en campos.

Si aparece un campo acompañado por una explicación, definición o aclaración,
identifica solamente el campo.

Ejemplo:

"RUT"

"Composición del RUT (Registro Único Tributario) en Uruguay"

"El RUT es un número que identifica a la empresa..."

El único campo es:

{{
  "campo": "RUT",
  "tipo": "numero"
}}

NO incluyas:

"Composición del RUT (Registro Único Tributario) en Uruguay"

NO incluyas:

"El RUT es un número que identifica a la empresa..."

--------------------------------------------------

REGLA 4:
No conviertas un título o nombre de sección en un campo.

Ejemplos que NO deben incluirse si solamente funcionan como títulos:

- Datos de contacto
- Información de la empresa
- Información personal
- Aspectos legales
- Legal
- Datos de la organización
- Antecedentes

Pero sí debes incluir los campos concretos que aparecen dentro de esas
secciones.

Ejemplo:

"Datos de contacto"

"Teléfono de contacto"

"E-mail"

En este caso:

NO incluir:
"Datos de contacto"

SÍ incluir:
"Teléfono de contacto"
"E-mail"

--------------------------------------------------

REGLA 5:
No conviertas encabezados o categorías en campos.

Un texto que solamente organiza o clasifica otros campos no es un campo.

Por ejemplo:

"Información de la empresa"

no es un campo.

Pero:

"Nombre de la empresa"

sí es un campo.

--------------------------------------------------

REGLA 6:
No conviertas instrucciones en campos.

Ejemplos:

"Complete los siguientes datos"

"Seleccione una opción"

"Indique la información solicitada"

NO son campos.

--------------------------------------------------

REGLA 7:
No conviertas explicaciones legales o informativas en campos.

Si un texto solamente informa al usuario y no requiere ingresar información,
seleccionar algo o realizar una acción, NO lo incluyas.

--------------------------------------------------

REGLA 8:
Las preguntas abiertas sí son campos.

Ejemplo:

"¿Cuáles son los principales problemas o desafíos que necesita resolver
en su empresa?"

Debe incluirse como:

{{
  "campo": "¿Cuáles son los principales problemas o desafíos que necesita resolver en su empresa?",
  "tipo": "pregunta"
}}

--------------------------------------------------

REGLA 9:
No inventes campos.

Identifica únicamente campos que estén presentes en el texto proporcionado.

No agregues campos porque sean comunes en otros formularios.

--------------------------------------------------

REGLA 10:
Analiza únicamente la página proporcionada.

Los campos pueden repetirse en otras páginas, pero no debes agregar campos
que no aparezcan en ESTA página.

==================================================
EJEMPLOS IMPORTANTES
==================================================

Ejemplo 1:

Texto:

RUT

Composición del RUT (Registro Único Tributario) en Uruguay

El RUT es un número que identifica a la empresa.

Respuesta:

[
  {{
    "campo": "RUT",
    "tipo": "numero"
  }}
]

--------------------------------------------------

Ejemplo 2:

Texto:

Nombre

Apellido

Género

Fecha de nacimiento

Respuesta:

[
  {{
    "campo": "Nombre",
    "tipo": "text"
  }},
  {{
    "campo": "Apellido",
    "tipo": "text"
  }},
  {{
    "campo": "Género",
    "tipo": "seleccion"
  }},
  {{
    "campo": "Fecha de nacimiento",
    "tipo": "fecha"
  }}
]

--------------------------------------------------

Ejemplo 3:

Texto:

Mujeres

Hombres

Personal total

Respuesta:

[
  {{
    "campo": "Mujeres",
    "tipo": "numero"
  }},
  {{
    "campo": "Hombres",
    "tipo": "numero"
  }},
  {{
    "campo": "Personal total",
    "tipo": "numero"
  }}
]

--------------------------------------------------

Ejemplo 4:

Texto:

¿En qué etapa se encuentra la empresa?

Respuesta:

[
  {{
    "campo": "¿En qué etapa se encuentra la empresa?",
    "tipo": "pregunta"
  }}
]

--------------------------------------------------

Ejemplo 5:

Texto:

Consentimiento de tratamiento de datos
[casilla para marcar]

Respuesta:

[
  {{
    "campo": "Consentimiento de tratamiento de datos",
    "tipo": "checkbox"
  }}
]

--------------------------------------------------

Ejemplo 6:

Texto:

Legal

Consentimiento de datos

Respuesta:

[
  {{
    "campo": "Consentimiento de datos",
    "tipo": "checkbox"
  }}
]

No incluir:

"Legal"

si solamente funciona como título de sección.

==================================================
QUÉ DEBES EXCLUIR
==================================================

NO incluyas:

- títulos generales del formulario
- títulos de secciones
- subtítulos
- encabezados
- nombres de categorías que solamente organizan el formulario
- instrucciones generales
- explicaciones
- definiciones
- ejemplos
- notas
- aclaraciones
- textos legales o informativos que no requieran una acción
- textos descriptivos
- información institucional
- nombres de secciones
- encabezados de tablas que solamente organizan información

==================================================
FORMATO DE RESPUESTA
==================================================

Devuelve ÚNICAMENTE un JSON válido.

No agregues explicaciones.

No agregues markdown.

No agregues comentarios.

No escribas texto antes ni después del JSON.

Cada objeto DEBE contener:

- "campo"
- "tipo"

Ejemplo de respuesta correcta:

[
  {{
    "campo": "RUT",
    "tipo": "numero"
  }},
  {{
    "campo": "Nombre",
    "tipo": "text"
  }},
  {{
    "campo": "Género",
    "tipo": "seleccion"
  }},
  {{
    "campo": "Fecha de nacimiento",
    "tipo": "fecha"
  }},
  {{
    "campo": "Mujeres",
    "tipo": "numero"
  }},
  {{
    "campo": "Consentimiento de datos",
    "tipo": "checkbox"
  }},
  {{
    "campo": "¿En qué etapa se encuentra la empresa?",
    "tipo": "pregunta"
  }}
]

Nunca devuelvas:

[
  {{
    "campo": "Mujeres"
  }}
]

Siempre devuelve:

[
  {{
    "campo": "Mujeres",
    "tipo": "numero"
  }}
]

==================================================
TEXTO DE LA PÁGINA A ANALIZAR
==================================================

{texto_pagina}
"""

    respuesta = llm.invoke(prompt)

    return respuesta.content

# ============================================================
# LIMPIAR RESPUESTA JSON
# ============================================================

def limpiar_respuesta_json(respuesta):

    texto = respuesta.strip()

    # Eliminar markdown
    texto = re.sub(
        r"```json\s*",
        "",
        texto,
        flags=re.IGNORECASE
    )

    texto = re.sub(
        r"```\s*",
        "",
        texto
    )

    inicio = texto.find("[")
    fin = texto.rfind("]")

    if inicio != -1 and fin != -1:
        texto = texto[inicio:fin + 1]

    # Intento normal
    try:
        return json.loads(texto)

    except json.JSONDecodeError as e:

        print(
            f"[QWEN] JSON inválido: {e}"
        )

        # Intentar recuperar objetos JSON individuales
        objetos = re.findall(
            r'\{\s*"campo"\s*:\s*"([^"]+)"(?:\s*,\s*"tipo"\s*:\s*"([^"]+)")?\s*\}',
            texto
        )

        recuperados = []

        for campo, tipo in objetos:

            item = {
                "campo": campo.strip()
            }

            if tipo:
                item["tipo"] = tipo.strip()

            recuperados.append(item)

        if recuperados:

            print(
                f"[QWEN] Objetos recuperados: "
                f"{len(recuperados)}"
            )

            return recuperados

        raise

# ============================================================
# LIMPIAR CAMPOS
# ============================================================

def limpiar_campos(campos):

    resultado = []
    vistos = set()

    tipos_validos = {
        "text",
        "numero",
        "fecha",
        "email",
        "seleccion",
        "checkbox",
        "pregunta"
    }

    for item in campos:

        if not isinstance(item, dict):
            continue

        campo = item.get("campo")
        tipo = item.get("tipo", "text")

        if not campo:
            continue

        campo = str(campo).strip()

        if not campo:
            continue

        campo = re.sub(
            r"\s+",
            " ",
            campo
        )

        tipo = str(tipo).strip().lower()

        if tipo not in tipos_validos:
            tipo = "text"

        campo_lower = campo.lower()

        # Evitar elementos generales
        if campo_lower in {
            "formulario",
            "formulario de postulación",
            "datos",
            "información",
            "informacion",
            "nombre o descripción del campo",
        }:
            continue

        clave = campo_lower

        if clave in vistos:
            continue

        vistos.add(clave)

        resultado.append({
            "campo": campo,
            "tipo": tipo
        })

    return resultado

# ============================================================
# EXTRAER PÁGINAS CON DOCLING
# ============================================================

def extraer_paginas_docling(ruta_formulario):

    ruta_formulario = Path(
        ruta_formulario
    )

    print(
        f"[DOCLING-FORMULARIO] Procesando: "
        f"{ruta_formulario.name}"
    )

    if not ruta_formulario.exists():

        raise FileNotFoundError(
            f"No existe el formulario: "
            f"{ruta_formulario}"
        )

    converter = DocumentConverter()

    resultado = converter.convert(
        str(ruta_formulario)
    )

    documento = resultado.document

    paginas = {}

    # ========================================================
    # RECORRER ELEMENTOS
    # ========================================================

    for item, _level in documento.iterate_items():

        provs = getattr(
            item,
            "prov",
            None
        )

        if not provs:
            continue

        for prov in provs:

            pagina = getattr(
                prov,
                "page_no",
                None
            )

            if pagina is None:
                continue

            texto = ""

            if hasattr(item, "text"):

                texto = item.text or ""

            if not texto:
                continue

            texto = texto.strip()

            if not texto:
                continue

            if pagina not in paginas:

                paginas[pagina] = []

            paginas[pagina].append(
                texto
            )

    # ========================================================
    # CONSTRUIR RESULTADO
    # ========================================================

    resultado_paginas = []

    for numero_pagina in sorted(
        paginas
    ):

        textos = paginas[
            numero_pagina
        ]

        contenido = "\n".join(
            textos
        )

        resultado_paginas.append({
            "pagina": numero_pagina,
            "contenido": contenido
        })

    print(
        f"[DOCLING-FORMULARIO] "
        f"Páginas encontradas: "
        f"{len(resultado_paginas)}"
    )

    for pagina in resultado_paginas:

        print(
            f"[DOCLING-FORMULARIO] "
            f"Página {pagina['pagina']}: "
            f"{len(pagina['contenido'])} caracteres"
        )

    return resultado_paginas


# ============================================================
# ELIMINAR DUPLICADOS
# ============================================================

def eliminar_duplicados_globales(campos):

    resultado = []

    vistos = set()

    for campo in campos:

        texto = campo["campo"].strip()

        clave = re.sub(
            r"\s+",
            " ",
            texto.lower()
        )

        if clave in vistos:
            continue

        vistos.add(clave)

        resultado.append(
            campo
        )

    return resultado


# ============================================================
# EXTRAER CAMPOS DEL FORMULARIO
# ============================================================

def extraer_campos_formulario(
    ruta_formulario: Path
):

    inicio_total = time.time()

    # ========================================================
    # 1. VALIDAR RUTA
    # ========================================================

    ruta_formulario = Path(
        ruta_formulario
    )

    print(
        f"[QWEN] Formulario recibido: "
        f"{ruta_formulario}"
    )

    if not ruta_formulario.exists():

        raise FileNotFoundError(
            f"No existe el formulario: "
            f"{ruta_formulario}"
        )

    # ========================================================
    # 2. EXTRAER PÁGINAS CON DOCLING
    # ========================================================

    paginas = extraer_paginas_docling(
        ruta_formulario
    )

    if not paginas:

        raise Exception(
            "Docling no pudo extraer "
            "ninguna página del formulario."
        )

    # ========================================================
    # 3. PROCESAR CADA PÁGINA CON QWEN
    # ========================================================

    todos_los_campos = []

    for pagina in paginas:

        numero_pagina = pagina[
            "pagina"
        ]

        contenido = pagina[
            "contenido"
        ]

        print()

        print(
            f"[QWEN] Procesando página "
            f"{numero_pagina}"
        )

        print(
            f"[QWEN] Caracteres: "
            f"{len(contenido)}"
        )

        try:

            # ------------------------------------------------
            # Ejecutar Qwen
            # ------------------------------------------------
            inicio = time.time()

            texto_respuesta = preguntar_qwen(
                contenido
            )

            tiempo = (
                time.time() - inicio
            )

            print(
                f"[QWEN] Tiempo página "
                f"{numero_pagina}: "
                f"{tiempo:.2f} segundos"
            )

            # =================================================
            # MOSTRAR RESPUESTA ORIGINAL
            # =================================================

            print()
            print(
                f"[QWEN] RESPUESTA ORIGINAL "
                f"PÁGINA {numero_pagina}"
            )

            print(
                "-" * 60
            )

            print(
                texto_respuesta
            )

            print(
                "-" * 60
            )

            # =================================================
            # PARSEAR JSON
            # =================================================

            campos = limpiar_respuesta_json(
                texto_respuesta
            )

            print(
                f"[QWEN] Candidatos encontrados: "
                f"{len(campos)}"
            )

            # =================================================
            # LIMPIAR CAMPOS
            # =================================================

            campos_limpios = limpiar_campos(
                campos
            )

            print(
                f"[QWEN] Después de limpieza: "
                f"{len(campos_limpios)}"
            )

            # =================================================
            # AGREGAR CAMPOS
            # =================================================

            for campo in campos_limpios:

                todos_los_campos.append({
                    "campo": campo["campo"],
                    "tipo": campo["tipo"],
                    "pagina": numero_pagina
                })

        except Exception as e:

            print(
                f"[QWEN] ERROR página "
                f"{numero_pagina}: "
                f"{e}"
            )

    # ========================================================
    # 4. LIMPIEZA GLOBAL
    # ========================================================

    print()

    print(
        "[QWEN] Aplicando limpieza global..."
    )

    todos_los_campos = (
        eliminar_duplicados_globales(
            todos_los_campos
        )
    )

    # ========================================================
    # 5. ASIGNAR IDs
    # ========================================================

    campos_finales = []

    for indice, campo in enumerate(
        todos_los_campos,
        start=1
    ):

        campos_finales.append({
            "id": indice,
            "campo": campo["campo"],
            "tipo": campo["tipo"],
            "pagina": campo["pagina"]
        })

    # ========================================================
    # 6. TIEMPO TOTAL
    # ========================================================

    tiempo_total = (
        time.time() - inicio_total
    )

    print()

    print(
        f"[QWEN] TOTAL DE CAMPOS: "
        f"{len(campos_finales)}"
    )

    print(
        f"[QWEN] TIEMPO TOTAL: "
        f"{tiempo_total:.2f} segundos"
    )

    return {

        "campos": campos_finales,

        "total": len(campos_finales)

    }