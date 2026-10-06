from pathlib import Path
from typing import Any

from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import (
    HuggingFaceTokenizer,
)
from transformers import AutoTokenizer
from sentence_transformers import SentenceTransformer


# ============================================================
# CONFIGURACIÓN
# ============================================================

EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

TOP_K = 3


# ============================================================
# MODELOS
# ============================================================

print("[EMBEDDING] Cargando modelo...")

embedding_model = SentenceTransformer(
    EMBEDDING_MODEL
)

print("[EMBEDDING] Modelo cargado")


# Tokenizer de HuggingFace para HybridChunker
hf_tokenizer = AutoTokenizer.from_pretrained(
    EMBEDDING_MODEL
)

tokenizer = HuggingFaceTokenizer(
    tokenizer=hf_tokenizer,
    max_tokens=512,
)

chunker = HybridChunker(
    tokenizer=tokenizer
)

converter = DocumentConverter()


# ============================================================
# PROCESAR UN DOCUMENTO
# ============================================================

def procesar_documento(ruta: Path) -> list[dict[str, Any]]:
    """
    Procesa un PDF con Docling y genera chunks.

    No guarda nada en la base de datos.
    """

    print()
    print("=" * 60)
    print(f"[DOCLING] Procesando: {ruta.name}")
    print("=" * 60)

    resultado = converter.convert(str(ruta))

    documento = resultado.document

    chunks = []

    for chunk in chunker.chunk(documento):

        texto = chunk.text.strip()

        if not texto:
            continue

        pagina = None

        # Intentamos obtener la página de origen
        try:
            if chunk.meta and chunk.meta.doc_items:
                for item in chunk.meta.doc_items:
                    if hasattr(item, "prov") and item.prov:
                        pagina = item.prov[0].page_no
                        break
        except Exception:
            pagina = None

        chunks.append({
            "documento": ruta.name,
            "pagina": pagina,
            "texto": texto,
        })

    print(
        f"[DOCLING] Chunks generados: {len(chunks)}"
    )

    return chunks


# ============================================================
# PROCESAR TODOS LOS DOCUMENTOS DEL JOB
# ============================================================

def generar_chunks_documentos(
    carpeta_job: Path,
    excluir: str | None = None,
) -> list[dict[str, Any]]:

    print()
    print("=" * 60)
    print("[DOCLING] GENERANDO CHUNKS DE DOCUMENTOS")
    print("=" * 60)

    todos_los_chunks = []

    archivos = sorted(
        carpeta_job.glob("*")
    )

    for archivo in archivos:

        if not archivo.is_file():
            continue

        # El formulario se procesa aparte
        if excluir and archivo.name.lower() == excluir.lower():
            print(
                f"[DOCLING] Omitiendo formulario: {archivo.name}"
            )
            continue

        # Por ahora procesamos PDFs
        if archivo.suffix.lower() != ".pdf":
            print(
                f"[DOCLING] Omitiendo archivo no PDF: {archivo.name}"
            )
            continue

        try:

            chunks = procesar_documento(
                archivo
            )

            todos_los_chunks.extend(
                chunks
            )

        except Exception as e:

            print(
                f"[DOCLING] Error procesando "
                f"{archivo.name}: {e}"
            )

    print()
    print(
        f"[DOCLING] TOTAL DE CHUNKS: "
        f"{len(todos_los_chunks)}"
    )

    return todos_los_chunks


# ============================================================
# GENERAR EMBEDDINGS
# ============================================================

def generar_embeddings(
    chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    if not chunks:
        print(
            "[EMBEDDING] No hay chunks para procesar"
        )
        return []

    print()
    print("=" * 60)
    print("[EMBEDDING] GENERANDO EMBEDDINGS")
    print("=" * 60)

    textos = [
        chunk["texto"]
        for chunk in chunks
    ]

    # Para E5 recomendamos prefijo passage:
    textos_embedding = [
        f"passage: {texto}"
        for texto in textos
    ]

    embeddings = embedding_model.encode(
        textos_embedding,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    for chunk, embedding in zip(
        chunks,
        embeddings,
    ):

        chunk["embedding"] = embedding.tolist()

    print(
        f"[EMBEDDING] Embeddings generados: "
        f"{len(embeddings)}"
    )

    if len(embeddings) > 0:
        print(
            f"[EMBEDDING] Dimensión: "
            f"{len(embeddings[0])}"
        )

    return chunks


# ============================================================
# EMBEDDING DE UN CAMPO
# ============================================================

def generar_embedding_campo(
    campo: str,
) -> list[float]:

    texto = f"query: {campo}"

    embedding = embedding_model.encode(
        texto,
        normalize_embeddings=True,
    )

    return embedding.tolist()


# ============================================================
# SIMILITUD COSENO
# ============================================================

def similitud_coseno(
    vector_a: list[float],
    vector_b: list[float],
) -> float:

    producto = sum(
        a * b
        for a, b in zip(
            vector_a,
            vector_b,
        )
    )

    norma_a = sum(
        a * a
        for a in vector_a
    ) ** 0.5

    norma_b = sum(
        b * b
        for b in vector_b
    ) ** 0.5

    if norma_a == 0 or norma_b == 0:
        return 0.0

    return producto / (
        norma_a * norma_b
    )


# ============================================================
# BUSCAR CHUNKS RELEVANTES
# ============================================================

def buscar_chunks_relevantes(
    campo: str,
    chunks: list[dict[str, Any]],
    top_k: int = TOP_K,
) -> list[dict[str, Any]]:

    if not chunks:
        return []

    print()
    print("=" * 60)
    print("[BUSQUEDA SEMÁNTICA]")
    print(f"Campo: {campo}")
    print("=" * 60)

    embedding_campo = generar_embedding_campo(
        campo
    )

    resultados = []

    for chunk in chunks:

        similitud = similitud_coseno(
            embedding_campo,
            chunk["embedding"],
        )

        resultados.append({
            "documento": chunk["documento"],
            "pagina": chunk["pagina"],
            "texto": chunk["texto"],
            "similitud": similitud,
        })

    resultados.sort(
        key=lambda x: x["similitud"],
        reverse=True,
    )

    resultados = resultados[:top_k]

    for indice, resultado in enumerate(
        resultados,
        start=1,
    ):

        print()
        print(
            f"[{indice}] "
            f"Similitud: "
            f"{resultado['similitud']:.4f}"
        )

        print(
            f"Documento: "
            f"{resultado['documento']}"
        )

        print(
            f"Página: "
            f"{resultado['pagina']}"
        )

        print(
            f"Texto: "
            f"{resultado['texto'][:500]}"
        )

    return resultados