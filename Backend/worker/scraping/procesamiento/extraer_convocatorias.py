import json
import re
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation

import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from sentence_transformers import SentenceTransformer
import traceback

# ============================================================
# CONFIGURACIÓN
# ============================================================

# ------------------------------------------------------------
# PostgreSQL
# ------------------------------------------------------------

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 15432,
    "dbname": "interfascia",
    "user": "interfascia",
    "password": "interfascia_dev_change_me"
}


# ------------------------------------------------------------
# Ollama
# ------------------------------------------------------------

OLLAMA_URL = "http://localhost:11434"

QWEN_MODEL = "qwen2.5:3b-instruct"


# ------------------------------------------------------------
# Embeddings
# ------------------------------------------------------------

# DEBE ser el mismo modelo utilizado para crear chunk.embedding
EMBED_MODEL = "intfloat/multilingual-e5-small"

EXPECTED_EMBEDDING_DIM = 384


# ------------------------------------------------------------
# RAG
# ------------------------------------------------------------

# Cantidad de chunks obtenidos por búsqueda semántica
TOP_K_SEMANTIC = 2

# Cantidad de chunks encontrados por cada keyword
TOP_K_KEYWORD = 3

# Máximo de chunks que se enviarán a Qwen
MAX_CONTEXT_CHUNKS = 10

# Máximo de caracteres del contexto enviado a Qwen
MAX_CONTEXT_CHARS = 8000


# ------------------------------------------------------------
# Pruebas
# ------------------------------------------------------------

# Primera prueba: una sola convocatoria.
# Después poner None para todas.
LIMIT_CONVOCATORIAS = None

# True = no reemplazar campos que ya tengan información.
SOLO_CAMPOS_VACIOS = True

# Procesar solamente este campo.
# Usar None para procesar todos los campos vacíos.
SOLO_CAMPOS = ["requisitos"]

# ============================================================
# CAMPOS QUE QUEREMOS EXTRAER
# ============================================================

CAMPOS = {

    "institucion": {
        "pregunta": (
            "¿Qué institución, organismo u organización "
            "gestiona, administra o financia esta convocatoria?"
        ),
        "tipo": "texto",
        "keywords": [
            "ANDE",
            "Agencia Nacional de Desarrollo"
        ]
    },

    "fecha_apertura": {
        "pregunta": (
            "Busca en el documento la fecha exacta de apertura "
            "o inicio del período de postulaciones. "
            "¿Desde qué fecha se puede postular?"
        ),
        "tipo": "fecha",
        "keywords": [
            "apertura",
            "inicio",
            "desde",
            "postular"
        ]
    },

    "fecha_cierre": {
        "pregunta": (
            "Busca en el documento la fecha exacta de cierre, "
            "vencimiento o fecha límite del período de postulaciones. "
            "¿Hasta qué fecha se puede postular?"
        ),
        "tipo": "fecha",
        "keywords": [
            "cierre",
            "vencimiento",
            "hasta",
            "postular"
        ]
    },

    "descripcion": {
        "pregunta": (
            "¿Cuál es el objetivo principal de la convocatoria "
            "y qué tipo de proyectos busca apoyar?"
        ),
        "tipo": "texto",
        "keywords": [
            "objetivo",
            "programa",
            "proyectos",
            "buscamos apoyar"
        ]
    },

    "beneficiarios": {
        "pregunta": (
            "¿Quiénes pueden ser beneficiarios de esta convocatoria? "
            "Extrae las personas, empresas o instituciones que pueden "
            "postular y sus condiciones de elegibilidad."
        ),
        "tipo": "texto",
        "keywords": [
            "beneficiarios",
            "pueden ser",
            "postulantes",
            "elegibilidad"
        ]
    },

    "requisitos": {
        "pregunta": (
            "Identifica los requisitos concretos que deben cumplir "
            "los postulantes para poder participar en esta convocatoria. "
            "Incluye condiciones de elegibilidad, antigüedad, situación "
            "fiscal, documentación obligatoria, certificados, registros "
            "y cualquier otra condición explícita exigida para postular. "
            "No incluyas información sobre objetivos, financiamiento o "
            "criterios de evaluación salvo que sean requisitos obligatorios."
        ),
        "tipo": "texto",
        "keywords": [
            "requisitos",
            "requisito",
            "condiciones",
            "condición",
            "elegibilidad",
            "elegible",
            "beneficiarios",
            "deberán cumplir",
            "deben cumplir",
            "podrán participar",
            "podrán postular",
            "postularse",
            "postulación",
            "documentación obligatoria",
            "documentos obligatorios",
            "certificado",
            "antigüedad",
            "no podrán"
        ]
    },

    "financiamiento": {
        "pregunta": (
            "¿Cuál es el monto de financiamiento, subsidio, aporte "
            "o beneficio económico indicado explícitamente "
            "para esta convocatoria?"
        ),
        "tipo": "numero",
        "keywords": [
            "financiamiento",
            "fondos",
            "monto",
            "apoyo",
            "subsidio",
            "$U"
        ]
    }
}


# ============================================================
# MODELO DE EMBEDDINGS
# ============================================================

print("=" * 70)
print("PROGRAMA 2 - EXTRACCIÓN DE DATOS DE CONVOCATORIAS")
print("=" * 70)

print("\n[1/6] Cargando modelo de embeddings...")

embedding_model = SentenceTransformer(
    EMBED_MODEL
)

# Método actualizado
embedding_dim = (
    embedding_model.get_embedding_dimension()
)

print(
    f"      Modelo: {EMBED_MODEL}"
)

print(
    f"      Dimensión: {embedding_dim}"
)


if embedding_dim != EXPECTED_EMBEDDING_DIM:

    raise ValueError(
        f"El modelo genera {embedding_dim} dimensiones, "
        f"pero PostgreSQL utiliza "
        f"vector({EXPECTED_EMBEDDING_DIM})."
    )


# ============================================================
# CONEXIÓN
# ============================================================

def obtener_conexion():

    return psycopg2.connect(
        **DB_CONFIG
    )


# ============================================================
# VECTOR -> PGVECTOR
# ============================================================

def vector_to_pgvector(vector):

    valores = [
        f"{float(valor):.10f}"
        for valor in vector
    ]

    return "[" + ",".join(valores) + "]"


# ============================================================
# CREAR EMBEDDING DE CONSULTA
# ============================================================

def generar_embedding_query(pregunta):

    texto = "query: " + pregunta

    embedding = embedding_model.encode(
        texto,
        normalize_embeddings=True,
        convert_to_numpy=True
    )

    if len(embedding) != EXPECTED_EMBEDDING_DIM:

        raise ValueError(
            f"Embedding inválido: "
            f"{len(embedding)} dimensiones"
        )

    return vector_to_pgvector(
        embedding
    )


# ============================================================
# OBTENER CHUNKS RELEVANTES
# ============================================================

def buscar_chunks(
    cur,
    convocatoria_id,
    pregunta,
    keywords
):

    embedding_query = generar_embedding_query(
        pregunta
    )

    chunks = {}

    # ========================================================
    # 1. BÚSQUEDA SEMÁNTICA
    # ========================================================

    cur.execute(
        """
        SELECT
            ch.id,
            ch.documento_id,
            ch.contenido,
            ch.pagina,
            ch.embedding <=> %s::vector AS distancia
        FROM chunk ch
        INNER JOIN documento d
            ON d.id = ch.documento_id
        WHERE d.convocatoria_id = %s
          AND ch.embedding IS NOT NULL
        ORDER BY ch.embedding <=> %s::vector
        LIMIT %s
        """,
        (
            embedding_query,
            convocatoria_id,
            embedding_query,
            TOP_K_SEMANTIC
        )
    )

    resultados_semanticos = cur.fetchall()

    for resultado in resultados_semanticos:

        chunk_id = resultado[0]

        distancia = float(
            resultado[4]
        )

        chunks[chunk_id] = {
            "chunk_id": chunk_id,
            "documento_id": resultado[1],
            "contenido": resultado[2],
            "pagina": resultado[3],
            "distancia": distancia,
            "similitud": 1 - distancia,
            "keyword_hits": 0,
            "origen": "semantico"
        }


    # ========================================================
    # 2. BÚSQUEDA POR PALABRAS CLAVE
    # ========================================================

    for keyword in keywords:

        patron = f"%{keyword}%"

        cur.execute(
            """
            SELECT
                ch.id,
                ch.documento_id,
                ch.contenido,
                ch.pagina
            FROM chunk ch
            INNER JOIN documento d
                ON d.id = ch.documento_id
            WHERE d.convocatoria_id = %s
              AND ch.contenido ILIKE %s
            ORDER BY ch.id
            LIMIT %s
            """,
            (
                convocatoria_id,
                patron,
                TOP_K_KEYWORD
            )
        )

        resultados_keyword = cur.fetchall()

        for resultado in resultados_keyword:

            chunk_id = resultado[0]

            if chunk_id not in chunks:

                chunks[chunk_id] = {
                    "chunk_id": chunk_id,
                    "documento_id": resultado[1],
                    "contenido": resultado[2],
                    "pagina": resultado[3],
                    "distancia": None,
                    "similitud": None,
                    "keyword_hits": 1,
                    "origen": "keyword"
                }

            else:

                chunks[chunk_id]["keyword_hits"] += 1

                chunks[chunk_id]["origen"] = (
                    "semantico+keyword"
                )


    # ========================================================
    # 3. SCORE HÍBRIDO
    # ========================================================

    for chunk in chunks.values():

        similitud = chunk["similitud"]

        keyword_hits = chunk["keyword_hits"]

        if similitud is None:

            # Los chunks encontrados solamente por keyword
            # reciben un score basado en coincidencias.
            chunk["score"] = (
                0.15 +
                (0.05 * keyword_hits)
            )

        else:

            # Los chunks semánticos mantienen como base
            # su similitud y reciben un pequeño refuerzo
            # por coincidencias exactas.
            chunk["score"] = (
                similitud +
                (0.03 * keyword_hits)
            )


    # ========================================================
    # 4. SELECCIÓN
    # ========================================================

    resultados_semanticos = [
        chunk
        for chunk in chunks.values()
        if chunk["origen"] in (
            "semantico",
            "semantico+keyword"
        )
    ]

    resultados_keywords = [
        chunk
        for chunk in chunks.values()
        if chunk["origen"] == "keyword"
    ]


    # Ordenar semánticos
    resultados_semanticos.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    # Ordenar keywords
    resultados_keywords.sort(
        key=lambda x: (
            x["keyword_hits"],
            x["score"]
        ),
        reverse=True
    )


    # ========================================================
    # 5. COMBINAR
    # ========================================================

    resultados_finales = []

    ids_agregados = set()


    # Primero agregamos los semánticos
    for chunk in resultados_semanticos:

        if len(resultados_finales) >= TOP_K_SEMANTIC:

            break

        resultados_finales.append(
            chunk
        )

        ids_agregados.add(
            chunk["chunk_id"]
        )


    # Después agregamos los encontrados exclusivamente
    # por keywords.
    for chunk in resultados_keywords:

        if len(resultados_finales) >= MAX_CONTEXT_CHUNKS:

            break

        if chunk["chunk_id"] in ids_agregados:

            continue

        resultados_finales.append(
            chunk
        )

        ids_agregados.add(
            chunk["chunk_id"]
        )


    return resultados_finales

def buscar_chunks_requisitos(
    cur,
    convocatoria_id,
    pregunta
):

    # ========================================================
    # EMBEDDING DE LA PREGUNTA
    # ========================================================

    embedding_query = generar_embedding_query(
        pregunta
    )

    chunks = {}

    conn = cur.connection

    with conn.cursor(
        cursor_factory=RealDictCursor
    ) as rcur:

        # ====================================================
        # 1. BÚSQUEDA SEMÁNTICA
        # ====================================================

        rcur.execute(
            """
            SELECT
                ch.id AS chunk_id,
                ch.documento_id AS documento_id,
                ch.contenido AS contenido,
                ch.pagina AS pagina,
                ch.embedding <=> %s::vector AS distancia
            FROM chunk ch
            INNER JOIN documento d
                ON d.id = ch.documento_id
            WHERE d.convocatoria_id = %s
              AND ch.embedding IS NOT NULL
            ORDER BY ch.embedding <=> %s::vector
            LIMIT 3
            """,
            (
                embedding_query,
                convocatoria_id,
                embedding_query
            )
        )

        resultados_semanticos = rcur.fetchall()

        print(
            f"      → Resultados semánticos: "
            f"{len(resultados_semanticos)}"
        )

        for fila in resultados_semanticos:

            chunk_id = fila["chunk_id"]

            distancia = float(
                fila["distancia"]
            )

            chunks[chunk_id] = {
                "chunk_id": chunk_id,
                "documento_id": fila["documento_id"],
                "contenido": fila["contenido"],
                "pagina": fila["pagina"],
                "distancia": distancia,
                "similitud": 1 - distancia,
                "keyword_hits": 0,
                "keyword_score": 0,
                "origen": "semantico"
            }

        # ====================================================
        # 2. BÚSQUEDA TEXTUAL ESPECIALIZADA
        # ====================================================

        rcur.execute(
            """
            SELECT
                ch.id AS chunk_id,
                ch.documento_id AS documento_id,
                ch.contenido AS contenido,
                ch.pagina AS pagina,

                (
                    CASE
                        WHEN ch.contenido ILIKE '%%requisit%%'
                        THEN 6 ELSE 0
                    END

                    +

                    CASE
                        WHEN ch.contenido ILIKE '%%elegibilidad%%'
                        THEN 6 ELSE 0
                    END

                    +

                    CASE
                        WHEN ch.contenido ILIKE '%%documentación obligatoria%%'
                        THEN 7 ELSE 0
                    END

                    +

                    CASE
                        WHEN ch.contenido ILIKE '%%documentos obligatorios%%'
                        THEN 7 ELSE 0
                    END

                    +

                    CASE
                        WHEN ch.contenido ILIKE '%%deberán cumplir%%'
                        THEN 5 ELSE 0
                    END

                    +

                    CASE
                        WHEN ch.contenido ILIKE '%%deben cumplir%%'
                        THEN 5 ELSE 0
                    END

                    +

                    CASE
                        WHEN ch.contenido ILIKE '%%podrán participar%%'
                        THEN 4 ELSE 0
                    END

                    +

                    CASE
                        WHEN ch.contenido ILIKE '%%postularse%%'
                        THEN 4 ELSE 0
                    END

                    +

                    CASE
                        WHEN ch.contenido ILIKE '%%certificado%%'
                        THEN 3 ELSE 0
                    END

                    +

                    CASE
                        WHEN ch.contenido ILIKE '%%antigüedad%%'
                        THEN 3 ELSE 0
                    END

                    +

                    CASE
                        WHEN ch.contenido ILIKE '%%no podrán%%'
                        THEN 3 ELSE 0
                    END

                ) AS keyword_score

            FROM chunk ch

            INNER JOIN documento d
                ON d.id = ch.documento_id

            WHERE d.convocatoria_id = %s

              AND (
                  ch.contenido ILIKE '%%requisit%%'
                  OR ch.contenido ILIKE '%%elegibilidad%%'
                  OR ch.contenido ILIKE '%%documentación obligatoria%%'
                  OR ch.contenido ILIKE '%%documentos obligatorios%%'
                  OR ch.contenido ILIKE '%%deberán cumplir%%'
                  OR ch.contenido ILIKE '%%deben cumplir%%'
                  OR ch.contenido ILIKE '%%podrán participar%%'
                  OR ch.contenido ILIKE '%%postularse%%'
                  OR ch.contenido ILIKE '%%certificado%%'
                  OR ch.contenido ILIKE '%%antigüedad%%'
                  OR ch.contenido ILIKE '%%no podrán%%'
              )

            ORDER BY keyword_score DESC

            LIMIT 8
            """,
            (
                convocatoria_id,
            )
        )

        resultados_keyword = rcur.fetchall()

        print(
            f"      → Resultados keyword: "
            f"{len(resultados_keyword)}"
        )

        for fila in resultados_keyword:

            chunk_id = fila["chunk_id"]

            keyword_score = int(
                fila["keyword_score"]
            )

            if chunk_id not in chunks:

                chunks[chunk_id] = {
                    "chunk_id": chunk_id,
                    "documento_id": fila["documento_id"],
                    "contenido": fila["contenido"],
                    "pagina": fila["pagina"],
                    "distancia": None,
                    "similitud": None,
                    "keyword_hits": 1,
                    "keyword_score": keyword_score,
                    "origen": "keyword"
                }

            else:

                chunks[chunk_id]["keyword_score"] = (
                    keyword_score
                )

                chunks[chunk_id]["keyword_hits"] += 1

                chunks[chunk_id]["origen"] = (
                    "semantico+keyword"
                )

    # ========================================================
    # 3. SCORE HÍBRIDO
    # ========================================================

    for chunk in chunks.values():

        similitud = chunk["similitud"]

        keyword_score = chunk["keyword_score"]

        if similitud is None:

            chunk["score"] = (
                0.10 +
                keyword_score / 100
            )

        else:

            chunk["score"] = (
                similitud +
                keyword_score / 100
            )

    # ========================================================
    # 4. ORDENAR
    # ========================================================

    resultados_finales = list(
        chunks.values()
    )

    resultados_finales.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    # ========================================================
    # 5. DEVOLVER
    # ========================================================

    return resultados_finales[:10]

# ============================================================
# CONSTRUIR CONTEXTO PARA QWEN
# ============================================================

def construir_contexto(chunks):

    bloques = []
    caracteres_totales = 0

    contenidos_vistos = set()

    for i, chunk in enumerate(
        chunks,
        start=1
    ):

        contenido = chunk["contenido"].strip()

        # -----------------------------------------------
        # Evitar exactamente el mismo contenido
        # -----------------------------------------------

        contenido_normalizado = (
            " ".join(
                contenido.lower().split()
            )
        )

        if contenido_normalizado in contenidos_vistos:
            continue

        contenidos_vistos.add(
            contenido_normalizado
        )

        bloque = (
            f"\n--- FRAGMENTO {i} ---\n"
            f"Chunk ID: {chunk['chunk_id']}\n"
            f"Origen: {chunk['origen']}\n\n"
            f"{contenido}\n"
        )

        if (
            caracteres_totales +
            len(bloque)
        ) > MAX_CONTEXT_CHARS:

            break

        bloques.append(
            bloque
        )

        caracteres_totales += len(
            bloque
        )

    return "\n".join(
        bloques
    )

# ============================================================
# PROMPT PARA QWEN
# ============================================================

def construir_prompt(
    campo,
    pregunta,
    contexto
):

    if campo == "requisitos":

        formato = """
{
    "respuesta": "- Requisito 1\\n- Requisito 2\\n- Requisito 3"
}
"""

        instrucciones_extra = """
Para requisitos:

- Devuelve un único texto.
- Usa una viñeta por requisito.
- No repitas requisitos.
- Si dos fragmentos contienen el mismo requisito, escríbelo una sola vez.
- Agrupa requisitos equivalentes.
- Incluye solamente requisitos o condiciones necesarias para postular.
- No incluyas objetivos, descripción del programa, financiamiento,
  gastos elegibles, evaluación ni información institucional.
- No inventes requisitos.
- Mantén la respuesta lo más compacta posible.
"""

    elif campo == "beneficiarios":

        formato = """
{
    "respuesta": "Descripción de los beneficiarios"
}
"""

        instrucciones_extra = """
Para beneficiarios:

- Devuelve un único texto.
- Describe quiénes pueden postular.
- Incluye las condiciones de elegibilidad relevantes.
- No repitas información.
"""

    else:

        formato = """
{
    "respuesta": null
}
"""

        instrucciones_extra = ""


    return f"""
Eres un sistema de extracción de información de
convocatorias y fondos de postulación.

Tu tarea es responder la pregunta utilizando
EXCLUSIVAMENTE la información contenida en los
fragmentos proporcionados.

REGLAS:

1. No inventes información.
2. No uses conocimiento externo.
3. Si la información no aparece claramente, devuelve null.
4. Usa únicamente los fragmentos proporcionados.
5. Para fechas utiliza formato YYYY-MM-DD cuando sea posible.
6. Para financiamiento devuelve solamente el número.
7. Mantén la respuesta concisa.
8. Devuelve exclusivamente JSON válido.
9. No repitas información encontrada en varios fragmentos.

{instrucciones_extra}

CAMPO:

{campo}

PREGUNTA:

{pregunta}

FRAGMENTOS:

{contexto}

FORMATO OBLIGATORIO:

{formato}
"""
# ============================================================
# LLAMAR A QWEN
# ============================================================

def consultar_qwen(prompt):

    payload = {

        "model": QWEN_MODEL,

        "messages": [

            {
                "role": "system",
                "content": (
                    "Eres un extractor de información "
                    "de documentos. "
                    "No inventes datos."
                )
            },

            {
                "role": "user",
                "content": prompt
            }
        ],

        "stream": False,

        "format": "json",

        "options": {
            "temperature": 0,
            "num_ctx": 4096,
            "num_predict": 600
        }
    }

    try:

        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
            timeout=300
        )

        response.raise_for_status()

    except requests.RequestException as e:

        raise RuntimeError(
            f"No se pudo conectar con Ollama: {e}"
        )

    data = response.json()

    contenido = (
        data
        .get("message", {})
        .get("content", "")
        .strip()
    )

    if not contenido:

        raise ValueError(
            "Qwen devolvió una respuesta vacía."
        )


    # ========================================================
    # JSON
    # ========================================================

    try:

        resultado = json.loads(
            contenido
        )

    except json.JSONDecodeError:

        match = re.search(
            r"\{.*\}",
            contenido,
            re.DOTALL
        )

        if not match:

            raise ValueError(
                "Qwen no devolvió JSON válido.\n"
                f"Respuesta:\n{contenido}"
            )

        resultado = json.loads(
            match.group(0)
        )

    return resultado


# ============================================================
# NORMALIZAR FECHAS
# ============================================================

def normalizar_fecha(valor):

    if valor is None:

        return None

    valor = str(
        valor
    ).strip()

    if not valor:

        return None


    # YYYY-MM-DD
    try:

        fecha = datetime.strptime(
            valor,
            "%Y-%m-%d"
        )

        return fecha.date()

    except ValueError:
        pass


    # DD/MM/YYYY
    try:

        fecha = datetime.strptime(
            valor,
            "%d/%m/%Y"
        )

        return fecha.date()

    except ValueError:
        pass


    # DD-MM-YYYY
    try:

        fecha = datetime.strptime(
            valor,
            "%d-%m-%Y"
        )

        return fecha.date()

    except ValueError:
        pass


    return None


# ============================================================
# NORMALIZAR NÚMERO
# ============================================================

def normalizar_numero(valor):

    if valor is None:

        return None


    if isinstance(
        valor,
        int
    ):

        return Decimal(
            valor
        )


    if isinstance(
        valor,
        float
    ):

        return Decimal(
            str(valor)
        )


    texto = str(valor).strip()

    if isinstance(valor, list):

        return "\n".join(
            [
                str(v)
                for v in valor
            ]
        )

    if not texto:
        return None


    # Eliminar símbolos
    texto = texto.replace(
        "$",
        ""
    )

    texto = texto.replace(
        "USD",
        ""
    )

    texto = texto.replace(
        "U$S",
        ""
    )

    texto = texto.replace(
        "UYU",
        ""
    )

    texto = texto.strip()


    # --------------------------------------------------------
    # Formatos:
    #
    # 500000
    # 500.000
    # 500,000
    # 500000.50
    # 500.000,50
    # --------------------------------------------------------

    if (
        "." in texto and
        "," in texto
    ):

        texto = texto.replace(
            ".",
            ""
        )

        texto = texto.replace(
            ",",
            "."
        )


    elif "," in texto:

        partes = texto.split(",")

        if (
            len(partes) == 2 and
            len(partes[1]) <= 2
        ):

            texto = texto.replace(
                ",",
                "."
            )

        else:

            texto = texto.replace(
                ",",
                ""
            )


    elif "." in texto:

        partes = texto.split(".")

        if (
            len(partes) == 2 and
            len(partes[1]) == 3
        ):

            texto = texto.replace(
                ".",
                ""
            )


    try:

        return Decimal(
            texto
        )

    except InvalidOperation:

        return None


# ============================================================
# NORMALIZAR RESULTADO
# ============================================================

def normalizar_resultado(
    campo,
    valor
):

    if valor is None:

        return None

    tipo = CAMPOS[
        campo
    ]["tipo"]


    if tipo == "fecha":

        return normalizar_fecha(
            valor
        )


    if tipo == "numero":

        return normalizar_numero(
            valor
        )


    texto = str(
        valor
    ).strip()

    if not texto:

        return None

    return texto


# ============================================================
# ACTUALIZAR CONVOCATORIA
# ============================================================

def actualizar_convocatoria(
    cur,
    convocatoria_id,
    campo,
    valor
):

    if valor is None:

        print(
            f"      → No se actualiza {campo}: "
            "información no encontrada."
        )

        return False


    query = f"""
        UPDATE convocatoria
        SET {campo} = %s
        WHERE id = %s
    """


    cur.execute(
        query,
        (
            valor,
            convocatoria_id
        )
    )

    return True


# ============================================================
# OBTENER CONVOCATORIAS
# ============================================================

def obtener_convocatorias(
    cur
):

    query = """
        SELECT
            id,
            titulo,
            estado,
            institucion,
            fecha_apertura,
            fecha_cierre,
            descripcion,
            beneficiarios,
            requisitos,
            financiamiento
        FROM convocatoria
        WHERE requisitos IS NULL
        ORDER BY id
    """

    if LIMIT_CONVOCATORIAS is not None:

        query += (
            f" LIMIT {int(LIMIT_CONVOCATORIAS)}"
        )


    cur.execute(
        query
    )

    return cur.fetchall()


# ============================================================
# PROCESAR UNA CONVOCATORIA
# ============================================================

def procesar_convocatoria(
    cur,
    convocatoria
):

    convocatoria_id = convocatoria[0]
    titulo = convocatoria[1]
    estado = convocatoria[2]


    print("\n")
    print("=" * 70)

    print(
        f"CONVOCATORIA ID: {convocatoria_id}"
    )

    print(
        f"TÍTULO: {titulo}"
    )

    print(
        f"ESTADO: {estado}"
    )

    print("=" * 70)


    total_actualizados = 0


    # ========================================================
    # VALORES ACTUALES
    # ========================================================

    valores_actuales = {

        "institucion": convocatoria[3],

        "fecha_apertura": convocatoria[4],

        "fecha_cierre": convocatoria[5],

        "descripcion": convocatoria[6],

        "beneficiarios": convocatoria[7],

        "requisitos": convocatoria[8],

        "financiamiento": convocatoria[9]
    }


    # ========================================================
    # CAMPOS
    # ========================================================

    for campo, configuracion in CAMPOS.items():

        if (
            SOLO_CAMPOS is not None
            and campo not in SOLO_CAMPOS
        ):

            continue

        print(
            "\n" + "-" * 70
        )

        print(
            f"CAMPO: {campo}"
        )


        # ----------------------------------------------------
        # ¿Ya existe?
        # ----------------------------------------------------

        valor_actual = valores_actuales[
            campo
        ]


        if (
            SOLO_CAMPOS_VACIOS
            and valor_actual is not None
        ):

            print(
                f"      ✓ Ya tiene valor: "
                f"{valor_actual}"
            )

            print(
                "      → Se omite."
            )

            continue


        pregunta = configuracion[
            "pregunta"
        ]


        print(
            f"      Pregunta: {pregunta}"
        )


        # ----------------------------------------------------
        # BÚSQUEDA HÍBRIDA
        # ----------------------------------------------------

        print(
            "      → Buscando chunks..."
        )


        if campo == "requisitos":

            chunks = buscar_chunks_requisitos(
                cur,
                convocatoria_id,
                pregunta
            )

        else:

            chunks = buscar_chunks(
                cur,
                convocatoria_id,
                pregunta,
                configuracion["keywords"]
            )


        print(
            f"      → Chunks encontrados: "
            f"{len(chunks)}"
        )


        # ----------------------------------------------------
        # MOSTRAR CHUNKS
        # ----------------------------------------------------

        for chunk in chunks:

            if chunk["similitud"] is None:

                similitud = "N/A"

            else:

                similitud = (
                    f"{chunk['similitud']:.4f}"
                )


            if chunk.get("score") is None:

                score = "N/A"

            else:

                score = (
                    f"{chunk['score']:.4f}"
                )


            print(
                f"\n         "
                f"===== CHUNK {chunk['chunk_id']} ====="
            )


            print(
                f"         Similitud: "
                f"{similitud}"
            )


            print(
                f"         Keywords encontradas: "
                f"{chunk.get('keyword_hits', 0)}"
            )


            print(
                f"         Score híbrido: "
                f"{score}"
            )


            print(
                f"         Origen: "
                f"{chunk.get('origen', 'desconocido')}"
            )


            print(
                "         Contenido:"
            )


            print(
                chunk["contenido"][:500]
            )


        # ----------------------------------------------------
        # CONTEXTO
        # ----------------------------------------------------

        contexto = construir_contexto(
            chunks
        )


        if not contexto.strip():

            print(
                "      ⚠ No se pudo construir contexto."
            )

            continue


        # ----------------------------------------------------
        # PROMPT
        # ----------------------------------------------------

        prompt = construir_prompt(
            campo,
            pregunta,
            contexto
        )


        # ----------------------------------------------------
        # QWEN
        # ----------------------------------------------------

        print(
            "      → Consultando Qwen..."
        )


        inicio_qwen = time.time()


        resultado_qwen = consultar_qwen(
            prompt
        )


        tiempo_qwen = (
            time.time() -
            inicio_qwen
        )


        print(
            f"      → Tiempo Qwen: "
            f"{tiempo_qwen:.2f} s"
        )


        print(
            f"      → Respuesta Qwen: "
            f"{resultado_qwen}"
        )


        # ----------------------------------------------------
        # RESPUESTA
        # ----------------------------------------------------

        valor = resultado_qwen.get(
            "respuesta"
        )


        valor = normalizar_resultado(
            campo,
            valor
        )


        # ----------------------------------------------------
        # GUARDAR
        # ----------------------------------------------------

        if actualizar_convocatoria(
            cur,
            convocatoria_id,
            campo,
            valor
        ):

            print(
                f"      ✓ Guardado: "
                f"{campo} = {valor}"
            )

            total_actualizados += 1


    return total_actualizados


# ============================================================
# MAIN
# ============================================================

def main():

    inicio_total = time.time()


    print(
        "\n[2/6] Conectando a PostgreSQL..."
    )


    conn = obtener_conexion()


    procesadas = 0
    errores = 0
    campos_actualizados = 0


    try:

        with conn.cursor() as cur:

            print(
                "      ✓ Conexión correcta."
            )


            # ------------------------------------------------
            # Convocatorias
            # ------------------------------------------------

            convocatorias = obtener_convocatorias(
                cur
            )


            print(
                f"\n[3/6] Convocatorias a procesar: "
                f"{len(convocatorias)}"
            )


            for posicion, convocatoria in enumerate(
                convocatorias,
                start=1
            ):

                print(
                    f"\nPROGRESO: "
                    f"{posicion}/{len(convocatorias)}"
                )


                try:

                    cantidad = procesar_convocatoria(
                        cur,
                        convocatoria
                    )


                    # Commit individual
                    conn.commit()


                    procesadas += 1

                    campos_actualizados += (
                        cantidad
                    )


                    print(
                        "\n      ✓ Convocatoria "
                        "confirmada."
                    )


                except Exception as e:

                    conn.rollback()

                    errores += 1


                    print(
                        "\n      ✗ ERROR:"
                    )


                    print(
                        f"      {type(e).__name__}: "
                        f"{e}"
                    )

                    traceback.print_exc()


    finally:

        conn.close()


    # ========================================================
    # RESUMEN
    # ========================================================

    tiempo_total = (
        time.time() -
        inicio_total
    )


    minutos = int(
        tiempo_total // 60
    )


    segundos = (
        tiempo_total % 60
    )


    print("\n")
    print("=" * 70)
    print("PROCESAMIENTO FINALIZADO")
    print("=" * 70)


    print(
        f"Convocatorias:       "
        f"{len(convocatorias)}"
    )


    print(
        f"Procesadas:          "
        f"{procesadas}"
    )


    print(
        f"Errores:             "
        f"{errores}"
    )


    print(
        f"Campos actualizados: "
        f"{campos_actualizados}"
    )


    print(
        f"Tiempo total:        "
        f"{minutos} min "
        f"{segundos:.2f} seg"
    )


    print("=" * 70)


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":

    main()
