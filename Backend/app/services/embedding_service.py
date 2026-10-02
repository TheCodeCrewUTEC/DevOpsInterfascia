from sentence_transformers import SentenceTransformer


# CONFIGURACIÓN
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

print(
    f"[EMBEDDING] Cargando modelo: {EMBEDDING_MODEL}"
)

modelo = SentenceTransformer(
    EMBEDDING_MODEL
)

print(
    "[EMBEDDING] Modelo cargado correctamente"
)


# GENERAR EMBEDDINGS
def generar_embeddings(chunks: list[dict]) -> list[dict]:

    if not chunks:
        return []

    textos = [
        chunk["texto"]
        for chunk in chunks
    ]

    print(
        f"[EMBEDDING] Generando embeddings para "
        f"{len(textos)} chunks"
    )

    embeddings = modelo.encode(
        textos,
        normalize_embeddings=True,
        show_progress_bar=False
    )

    resultados = []

    for chunk, embedding in zip(
        chunks,
        embeddings
    ):

        resultados.append({
            "texto": chunk["texto"],
            "embedding": embedding.tolist()
        })

    print(
        f"[EMBEDDING] Embeddings generados: "
        f"{len(resultados)}"
    )

    if resultados:

        print(
            f"[EMBEDDING] Dimensiones: "
            f"{len(resultados[0]['embedding'])}"
        )

    return resultados