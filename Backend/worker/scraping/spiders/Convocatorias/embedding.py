import json
import time
from pathlib import Path

import psycopg2
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer
from ftfy import fix_text
from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import (
    HuggingFaceTokenizer
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

# Archivo generado por el Spider + Docling
JSON_FILE = Path("Fondos.json")


# -----------------------------
# PostgreSQL
# -----------------------------

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 15432,
    "dbname": "interfascia",
    "user": "interfascia",
    "password": "interfascia_dev_change_me"
}

# -----------------------------
# Embeddings
# -----------------------------

EMBED_MODEL = "intfloat/multilingual-e5-small"

# PostgreSQL:
# embedding vector(384)
EXPECTED_EMBEDDING_DIM = 384


# -----------------------------
# Chunking
# -----------------------------

MAX_TOKENS = 450

BATCH_SIZE = 16


# ============================================================
# INICIALIZACIÓN
# ============================================================

print("=" * 70)
print("FONDOS.JSON -> CHUNKS -> EMBEDDINGS -> POSTGRESQL")
print("=" * 70)


# ============================================================
# CARGAR MODELO DE EMBEDDINGS
# ============================================================

print("\n[1/5] Cargando modelo de embeddings...")

embedding_model = SentenceTransformer(
    EMBED_MODEL
)

embedding_dim = (
    embedding_model.get_sentence_embedding_dimension()
)

print(f"      Modelo: {EMBED_MODEL}")
print(f"      Dimensión: {embedding_dim}")


if embedding_dim != EXPECTED_EMBEDDING_DIM:

    raise ValueError(
        f"El modelo genera {embedding_dim} dimensiones, "
        f"pero la tabla chunk utiliza vector({EXPECTED_EMBEDDING_DIM})."
    )


# ============================================================
# CONFIGURAR TOKENIZER PARA DOCLING
# ============================================================

print("\n[2/5] Configurando tokenizer de HybridChunker...")

hf_tokenizer = AutoTokenizer.from_pretrained(
    EMBED_MODEL
)

tokenizer = HuggingFaceTokenizer(
    tokenizer=hf_tokenizer,
    max_tokens=MAX_TOKENS
)

chunker = HybridChunker(
    tokenizer=tokenizer,
    merge_peers=True
)

print(
    f"      Máximo de tokens por chunk: {MAX_TOKENS}"
)


# ============================================================
# BASE DE DATOS
# ============================================================

def obtener_conexion():

    return psycopg2.connect(
        **DB_CONFIG
    )


# ============================================================
# CARGAR JSON
# ============================================================

def cargar_fondos():

    if not JSON_FILE.exists():

        raise FileNotFoundError(
            f"No se encontró el archivo: {JSON_FILE.resolve()}"
        )

    print(
        f"\n      Leyendo: {JSON_FILE.resolve()}"
    )

    with open(
        JSON_FILE,
        "r",
        encoding="utf-8"
    ) as archivo:

        fondos = json.load(archivo)

    if not isinstance(fondos, list):

        raise ValueError(
            "Fondos.json debe contener una lista de registros."
        )

    return fondos


# ============================================================
# BUSCAR / CREAR CONVOCATORIA
# ============================================================

def obtener_convocatoria_id(
    cur,
    fondo
):

    titulo = fondo.get("nombre")

    if not titulo:

        raise ValueError(
            "El registro no tiene el campo 'nombre'."
        )

    # Buscar convocatoria existente
    cur.execute(
        """
        SELECT id
        FROM convocatoria
        WHERE titulo = %s
        LIMIT 1
        """,
        (titulo,)
    )

    resultado = cur.fetchone()

    if resultado:

        return resultado[0]


    # --------------------------------------------------------
    # Si no existe, crearla
    # --------------------------------------------------------

    estado = fondo.get("estado")

    cur.execute(
        """
        INSERT INTO convocatoria
        (
            titulo,
            estado
        )
        VALUES
        (
            %s,
            %s
        )
        RETURNING id
        """,
        (
            titulo,
            estado
        )
    )

    convocatoria_id = cur.fetchone()[0]

    print(
        f"      + Convocatoria creada: "
        f"{titulo} (ID {convocatoria_id})"
    )

    return convocatoria_id


# ============================================================
# BUSCAR / CREAR DOCUMENTO
# ============================================================

def obtener_documento_id(
    cur,
    convocatoria_id,
    fondo
):

    url = fondo.get("documento")

    if not url:

        raise ValueError(
            "El registro no tiene el campo 'documento'."
        )

    nombre = Path(
        url.split("?")[0]
    ).name

    if not nombre:

        nombre = "documento"

    # --------------------------------------------------------
    # Buscar documento existente
    # --------------------------------------------------------

    cur.execute(
        """
        SELECT id
        FROM documento
        WHERE convocatoria_id = %s
          AND url = %s
        LIMIT 1
        """,
        (
            convocatoria_id,
            url
        )
    )

    resultado = cur.fetchone()

    if resultado:

        return resultado[0]


    # --------------------------------------------------------
    # Crear documento
    # --------------------------------------------------------

    cur.execute(
        """
        INSERT INTO documento
        (
            convocatoria_id,
            nombre,
            url
        )
        VALUES
        (
            %s,
            %s,
            %s
        )
        RETURNING id
        """,
        (
            convocatoria_id,
            nombre,
            url
        )
    )

    documento_id = cur.fetchone()[0]

    print(
        f"      + Documento creado: "
        f"{nombre} (ID {documento_id})"
    )

    return documento_id


# ============================================================
# OBTENER PÁGINA
# ============================================================

def obtener_pagina(
    chunk
):

    try:

        paginas = []

        for item in chunk.meta.doc_items:

            for prov in getattr(
                item,
                "prov",
                []
            ):

                page_no = getattr(
                    prov,
                    "page_no",
                    None
                )

                if page_no is not None:

                    paginas.append(
                        page_no
                    )

        if paginas:

            return min(paginas)

    except Exception:

        pass

    return None


# ============================================================
# CREAR CHUNKS
# ============================================================

def crear_chunks(texto):

    from langchain_text_splitters import (
        RecursiveCharacterTextSplitter
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        separators=[
            "\n\n",
            "\n",
            ". ",
            " ",
            ""
        ]
    )

    textos = splitter.split_text(texto)

    chunks = []

    for i, contenido in enumerate(textos):

        contenido = contenido.strip()

        if not contenido:
            continue

        chunks.append({
            "numero": i,
            "contenido": contenido,
            "pagina": None
        })

    return chunks

# ============================================================
# EMBEDDINGS
# ============================================================

def generar_embeddings(
    chunks
):

    textos = []

    for chunk in chunks:

        textos.append(
            "passage: " +
            chunk["contenido"]
        )

    print(
        f"      Generando "
        f"{len(textos)} embeddings..."
    )

    embeddings = embedding_model.encode(
        textos,
        batch_size=BATCH_SIZE,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True
    )

    return embeddings


# ============================================================
# VECTOR -> PGVECTOR
# ============================================================

def vector_to_pgvector(
    vector
):

    valores = [
        f"{float(valor):.10f}"
        for valor in vector
    ]

    return "[" + ",".join(valores) + "]"


# ============================================================
# GUARDAR CHUNKS
# ============================================================

def guardar_chunks(
    cur,
    documento_id,
    chunks,
    embeddings
):

    # --------------------------------------------------------
    # Eliminar chunks anteriores
    # --------------------------------------------------------

    cur.execute(
        """
        DELETE FROM chunk
        WHERE documento_id = %s
        """,
        (
            documento_id,
        )
    )

    # --------------------------------------------------------
    # Insertar nuevos
    # --------------------------------------------------------

    for chunk, embedding in zip(
        chunks,
        embeddings
    ):

        vector = vector_to_pgvector(
            embedding
        )

        cur.execute(
            """
            INSERT INTO chunk
            (
                documento_id,
                contenido,
                pagina,
                embedding
            )
            VALUES
            (
                %s,
                %s,
                %s,
                CAST(%s AS vector)
            )
            """,
            (
                documento_id,
                chunk["contenido"],
                chunk["pagina"],
                vector
            )
        )


# ============================================================
# PROCESAR UN FONDO
# ============================================================

def procesar_fondo(cur, fondo):

    nombre = fondo.get("nombre", "SIN NOMBRE")
    estado = fondo.get("estado")
    url = fondo.get("documento")
    texto = fondo.get("texto")

    if not texto:
        print("      ⚠ No tiene texto")
        return 0

    # Corregir problemas de codificación
    texto = fix_text(texto)

    # Eliminar caracteres invisibles
    texto = texto.replace("\u200b", "")
    texto = texto.replace("\ufeff", "")

    # ========================================================
    # 1. CONVOCATORIA
    # ========================================================

    cur.execute(
        """
        SELECT id
        FROM convocatoria
        WHERE titulo = %s
        LIMIT 1
        """,
        (nombre,)
    )

    resultado = cur.fetchone()

    if resultado:
        convocatoria_id = resultado[0]

    else:

        cur.execute(
            """
            INSERT INTO convocatoria
            (
                titulo,
                estado
            )
            VALUES
            (
                %s,
                %s
            )
            RETURNING id
            """,
            (
                nombre,
                estado
            )
        )

        convocatoria_id = cur.fetchone()[0]

        print(
            f"      ✓ Convocatoria creada: "
            f"{convocatoria_id}"
        )

    # ========================================================
    # 2. DOCUMENTO
    # ========================================================

    cur.execute(
        """
        SELECT id
        FROM documento
        WHERE convocatoria_id = %s
          AND url = %s
        LIMIT 1
        """,
        (
            convocatoria_id,
            url
        )
    )

    resultado = cur.fetchone()

    if resultado:
        documento_id = resultado[0]

    else:

        nombre_documento = (
            Path(url.split("?")[0]).name
            if url
            else "documento"
        )

        cur.execute(
            """
            INSERT INTO documento
            (
                convocatoria_id,
                nombre,
                url
            )
            VALUES
            (
                %s,
                %s,
                %s
            )
            RETURNING id
            """,
            (
                convocatoria_id,
                nombre_documento,
                url
            )
        )

        documento_id = cur.fetchone()[0]

        print(
            f"      ✓ Documento creado: "
            f"{documento_id}"
        )

    # ========================================================
    # 3. CHUNKS
    # ========================================================

    print("      → Creando chunks...")

    chunks = crear_chunks(texto)

    print(
        f"      ✓ Chunks generados: "
        f"{len(chunks)}"
    )

    if not chunks:
        return 0

    # ========================================================
    # 4. EMBEDDINGS
    # ========================================================

    print("      → Generando embeddings...")

    embeddings = generar_embeddings(chunks)

    print(
        f"      ✓ Embeddings generados: "
        f"{len(embeddings)}"
    )

    # ========================================================
    # 5. VALIDACIÓN
    # ========================================================

    if len(chunks) != len(embeddings):

        raise ValueError(
            f"Cantidad diferente: "
            f"{len(chunks)} chunks / "
            f"{len(embeddings)} embeddings"
        )

    if embeddings.shape[1] != 384:

        raise ValueError(
            f"El embedding tiene "
            f"{embeddings.shape[1]} dimensiones "
            f"y PostgreSQL espera 384"
        )

    # ========================================================
    # 6. ELIMINAR CHUNKS ANTERIORES
    # ========================================================

    cur.execute(
        """
        DELETE FROM chunk
        WHERE documento_id = %s
        """,
        (documento_id,)
    )

    # ========================================================
    # 7. INSERTAR CHUNKS
    # ========================================================

    print("      → Guardando chunks en PostgreSQL...")

    cantidad_guardada = 0

    for chunk, embedding in zip(
        chunks,
        embeddings
    ):

        vector = vector_to_pgvector(
            embedding
        )

        cur.execute(
            """
            INSERT INTO chunk
            (
                documento_id,
                contenido,
                pagina,
                embedding
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s::vector
            )
            """,
            (
                documento_id,
                chunk["contenido"],
                chunk["pagina"],
                vector
            )
        )

        cantidad_guardada += 1

    print(
        f"      ✓ INSERT realizados: "
        f"{cantidad_guardada}"
    )

    return cantidad_guardada

# ============================================================
# MAIN
# ============================================================

def main():

    inicio_total = time.time()

    print("\n[1] Cargando Fondos.json...")

    fondos = cargar_fondos()

    print(
        f"    Registros encontrados: {len(fondos)}"
    )

    conn = obtener_conexion()

    procesados = 0
    errores = 0
    total_chunks = 0

    try:

        for posicion, fondo in enumerate(
            fondos,
            start=1
        ):

            print(
                f"\n{'=' * 70}"
            )

            print(
                f"FONDO {posicion}/{len(fondos)}"
            )

            try:

                with conn.cursor() as cur:

                    cantidad = procesar_fondo(
                        cur,
                        fondo
                    )

                # Commit SOLO de este fondo
                conn.commit()

                procesados += 1
                total_chunks += cantidad

                print(
                    f"      ✓ TRANSACCIÓN CONFIRMADA"
                )

            except Exception as e:

                conn.rollback()

                errores += 1

                print(
                    f"\n      ✗ ERROR:"
                )

                print(
                    f"      {type(e).__name__}: {e}"
                )

                print(
                    "      ↳ Se hizo ROLLBACK "
                    "de este fondo."
                )

    finally:

        conn.close()

    tiempo = time.time() - inicio_total

    print("\n")
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)

    print(
        f"Fondos:          {len(fondos)}"
    )

    print(
        f"Procesados:      {procesados}"
    )

    print(
        f"Errores:         {errores}"
    )

    print(
        f"Chunks creados:  {total_chunks}"
    )

    print(
        f"Tiempo:          "
        f"{int(tiempo // 60)} min "
        f"{tiempo % 60:.2f} seg"
    )

    print("=" * 70)

# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    main()