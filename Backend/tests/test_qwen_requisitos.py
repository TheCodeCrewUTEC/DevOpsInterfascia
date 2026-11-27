import importlib.util
import json
from pathlib import Path

import pytest

EXTRACTOR = (
    Path(__file__).resolve().parents[1]
    / "worker"
    / "scraping"
    / "procesamiento"
    / "extraer_convocatorias.py"
)

# Requisitos que sí están en los fragmentos de cada escenario.
DGI = "estar al día con DGI"
BPS = "estar al día con BPS"
ANTIGUEDAD = "antigüedad mínima de la empresa es de dos años"
CERTIFICADO_BPS = "presentar certificado de BPS"

# Datos que ningún fragmento de estos escenarios aporta.
INVENTADOS = ("garantía hipotecaria", "exportaciones", "RUT")


def cargar_extractor():
    spec = importlib.util.spec_from_file_location("extraer_convocatorias_qwen", EXTRACTOR)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def extractor():
    return cargar_extractor()


def fragmentos(*textos):
    return [
        {"chunk_id": indice, "origen": "keyword", "contenido": texto, "pagina": indice}
        for indice, texto in enumerate(textos, start=1)
    ]


def prompt_de(extractor, textos):
    contexto = extractor.construir_contexto(fragmentos(*textos))
    prompt = extractor.construir_prompt(
        "requisitos",
        extractor.CAMPOS["requisitos"]["pregunta"],
        contexto,
    )
    return contexto, prompt


class RespuestaHttp:
    def __init__(self, contenido):
        self._contenido = contenido

    def raise_for_status(self):
        return None

    def json(self):
        return {"message": {"content": self._contenido}}


class Cursor:
    def __init__(self):
        self.llamadas = []

    def execute(self, query, params=None):
        self.llamadas.append((query, params))


def guardar(extractor, respuesta):
    valor = extractor.normalizar_resultado("requisitos", respuesta)
    cursor = Cursor()
    guardado = extractor.actualizar_convocatoria(cursor, 7, "requisitos", valor)
    return valor, guardado, cursor


def test_prompt_con_requisitos_explicitos_lleva_solo_lo_respaldado(extractor):
    _, prompt = prompt_de(
        extractor,
        (
            f"Los postulantes deben cumplir: {DGI}.",
            f"También deben cumplir: {BPS}.",
            f"La {ANTIGUEDAD}.",
        ),
    )

    for requisito in (DGI, BPS, ANTIGUEDAD):
        assert requisito in prompt
    for inventado in INVENTADOS:
        assert inventado not in prompt
    assert "No inventes requisitos." in prompt
    assert "EXCLUSIVAMENTE" in prompt
    assert extractor.CAMPOS["requisitos"]["pregunta"] in prompt


def test_prompt_incompleto_no_agrega_condiciones_ausentes(extractor):
    _, prompt = prompt_de(extractor, (f"Los postulantes deben cumplir: {DGI}.",))

    assert DGI in prompt
    assert BPS not in prompt
    assert ANTIGUEDAD not in prompt
    assert "No inventes requisitos." in prompt
    assert "Si la información no aparece claramente, devuelve null." in prompt


def test_prompt_mixto_pide_quedarse_con_los_requisitos(extractor):
    _, prompt = prompt_de(
        extractor,
        (
            f"Los postulantes deben {CERTIFICADO_BPS}.",
            "El expediente 2026-EXP-44 se archiva en mesa de entrada de 9 a 17.",
            "El objetivo del programa es promover exportaciones de software.",
        ),
    )

    assert CERTIFICADO_BPS in prompt
    assert "2026-EXP-44" in prompt
    assert "exportaciones de software" in prompt
    assert "Incluye solamente requisitos o condiciones necesarias para postular." in prompt
    assert "No incluyas objetivos" in prompt


def test_sin_fragmentos_el_contexto_queda_vacio(extractor):
    assert extractor.construir_contexto([]) == ""


def test_sin_requisitos_el_prompt_pide_null(extractor):
    _, prompt = prompt_de(
        extractor,
        (
            "La oficina de Montevideo atiende de lunes a viernes.",
            "Se publicó la resolución en el diario oficial.",
        ),
    )

    assert "La oficina de Montevideo atiende de lunes a viernes." in prompt
    assert DGI not in prompt
    assert BPS not in prompt
    assert "No inventes requisitos." in prompt
    assert "devuelve null" in prompt


def test_consultar_qwen_interpreta_el_json_sin_llamar_a_ollama(extractor, monkeypatch):
    enviados = {}

    def post(url, json, timeout):
        enviados["url"] = url
        enviados["json"] = json
        enviados["timeout"] = timeout
        return RespuestaHttp(
            json_lib.dumps({"respuesta": f"- {DGI}\n- {BPS}"})
        )

    json_lib = json
    monkeypatch.setattr(extractor.requests, "post", post)

    resultado = extractor.consultar_qwen("PROMPT-DE-PRUEBA")

    assert enviados["url"] == f"{extractor.OLLAMA_URL}/api/chat"
    assert enviados["json"]["messages"][1]["content"] == "PROMPT-DE-PRUEBA"
    assert enviados["json"]["options"]["temperature"] == 0
    assert enviados["json"]["format"] == "json"
    assert resultado["respuesta"] == f"- {DGI}\n- {BPS}"


def test_la_respuesta_respaldada_se_guarda_sin_agregar_texto(extractor):
    respuesta = f"- {DGI}\n- {BPS}\n- La {ANTIGUEDAD}."
    valor, guardado, cursor = guardar(extractor, respuesta)

    assert guardado is True
    assert valor == respuesta
    for requisito in (DGI, BPS, ANTIGUEDAD):
        assert requisito in valor
    for inventado in INVENTADOS:
        assert inventado not in valor
    query, params = cursor.llamadas[0]
    assert "requisitos" in query
    assert params == (respuesta, 7)


def test_la_respuesta_parcial_no_completa_lo_que_falta(extractor):
    valor, guardado, _cursor = guardar(extractor, f"- {DGI}")

    assert guardado is True
    assert DGI in valor
    assert BPS not in valor
    assert ANTIGUEDAD not in valor
    assert CERTIFICADO_BPS not in valor


def test_null_o_vacio_no_guarda_requisitos(extractor):
    for respuesta in (None, "", "   "):
        valor, guardado, cursor = guardar(extractor, respuesta)
        assert valor is None
        assert guardado is False
        assert cursor.llamadas == []
