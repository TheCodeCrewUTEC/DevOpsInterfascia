import numpy as np
import pytest
from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-base"
EXPECTED_DIM = 768
TEXTO = "passage: Interfascia es una plataforma de vigilancia tecnológica."


@pytest.fixture(scope="module")
def model():
    return SentenceTransformer(MODEL_NAME)


def test_genera_embedding_con_forma_y_valores_validos(model):
    embedding = model.encode(TEXTO)

    print("Dimensiones:", embedding.shape)
    print("Embedding generado:", embedding[:10])

    assert isinstance(embedding, np.ndarray)
    assert embedding.shape == (EXPECTED_DIM,)
    assert np.issubdtype(embedding.dtype, np.floating)
    assert np.all(np.isfinite(embedding))
    assert not np.allclose(embedding, 0.0)


def test_el_mismo_texto_produce_el_mismo_embedding(model):
    primero = model.encode(TEXTO)
    segundo = model.encode(TEXTO)

    np.testing.assert_allclose(primero, segundo, rtol=1e-5, atol=1e-5)


def test_textos_distintos_producen_embeddings_distintos(model):
    otro = "passage: El clima en la Patagonia es frío y ventoso."

    embedding = model.encode(TEXTO)
    otro_embedding = model.encode(otro)

    assert embedding.shape == otro_embedding.shape == (EXPECTED_DIM,)
    assert not np.allclose(embedding, otro_embedding)