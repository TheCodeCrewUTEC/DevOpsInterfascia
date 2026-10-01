from docling.chunking import HybridChunker
from transformers import AutoTokenizer

from docling_core.transforms.chunker.tokenizer.huggingface import (
    HuggingFaceTokenizer
)


EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

# TOKENIZER
tokenizer = AutoTokenizer.from_pretrained(
    EMBEDDING_MODEL
)

hf_tokenizer = HuggingFaceTokenizer(
    tokenizer=tokenizer
)

# CHUNKER
chunker = HybridChunker(
    tokenizer=hf_tokenizer
)

# CHUNKING
def generar_chunks(documento):

    chunks = []

    for chunk in chunker.chunk(documento):

        texto = chunk.text

        if not texto or not texto.strip():
            continue

        chunks.append({
            "texto": texto,
        })

    return chunks