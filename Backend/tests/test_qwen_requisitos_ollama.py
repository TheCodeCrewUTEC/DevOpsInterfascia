"""Llamada real a Qwen local. No entra en el pytest habitual.

Correrla a mano, con Ollama levantado y el modelo ya descargado:

    set CORRER_QWEN=1
    python -m pytest tests/test_qwen_requisitos_ollama.py -q
"""

import os

import pytest

from test_qwen_requisitos import (
    ANTIGUEDAD,
    BPS,
    CERTIFICADO_BPS,
    DGI,
    cargar_extractor,
    prompt_de,
)

pytestmark = pytest.mark.skipif(
    os.getenv("CORRER_QWEN") != "1",
    reason="Prueba de Qwen local. Definí CORRER_QWEN=1 para ejecutarla.",
)


@pytest.fixture(scope="module")
def extractor():
    modulo = cargar_extractor()
    # .env apunta a host.docker.internal, que es el host visto desde el contenedor.
    # Esta prueba corre en la máquina, donde Ollama escucha en localhost.
    modulo.OLLAMA_URL = os.getenv("OLLAMA_URL_PRUEBA", "http://127.0.0.1:11434")
    return modulo


def generado(extractor, textos):
    _contexto, prompt = prompt_de(extractor, textos)
    resultado = extractor.consultar_qwen(prompt)
    return extractor.normalizar_resultado("requisitos", resultado.get("respuesta"))


def no_trae(texto, prohibidos):
    if texto is None:
        return
    bajo = texto.lower()
    for prohibido in prohibidos:
        assert prohibido.lower() not in bajo


def test_incluye_los_requisitos_del_fragmento_y_no_agrega_otros(extractor):
    texto = generado(
        extractor,
        (
            f"Los postulantes deben cumplir: {DGI}.",
            f"También deben cumplir: {BPS}.",
            f"La {ANTIGUEDAD}.",
        ),
    )

    assert texto
    bajo = texto.lower()
    assert "dgi" in bajo
    assert "bps" in bajo
    assert "dos años" in bajo or "2 años" in bajo
    no_trae(texto, ("garantía hipotecaria", "exportaciones", "rut", "cédula"))


def test_no_completa_requisitos_que_el_fragmento_no_tiene(extractor):
    texto = generado(extractor, (f"Los postulantes deben cumplir: {DGI}.",))

    assert texto
    assert "dgi" in texto.lower()
    no_trae(texto, ("bps", "antigüedad", "certificado", "rut", "cédula"))


def test_prioriza_el_requisito_sobre_el_texto_administrativo(extractor):
    texto = generado(
        extractor,
        (
            f"Los postulantes deben {CERTIFICADO_BPS}.",
            "El expediente 2026-EXP-44 se archiva en mesa de entrada de 9 a 17.",
            "El objetivo del programa es promover exportaciones de software.",
        ),
    )

    assert texto
    assert "bps" in texto.lower()
    no_trae(texto, ("2026-exp-44", "exportaciones", "9 a 17", "rut"))


def test_sin_requisitos_no_inventa_condiciones(extractor):
    texto = generado(
        extractor,
        (
            "La oficina de Montevideo atiende de lunes a viernes.",
            "Se publicó la resolución en el diario oficial.",
        ),
    )

    if isinstance(texto, str) and texto.strip().lower() == "null":
        texto = None

    no_trae(
        texto,
        (
            "dgi",
            "bps",
            "certificado",
            "antigüedad",
            "rut",
            "cédula",
            "dos años",
            "requisito 1",
            "requisito 2",
        ),
    )
