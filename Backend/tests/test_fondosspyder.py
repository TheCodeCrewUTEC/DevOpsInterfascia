import asyncio
import importlib.util
import re
from pathlib import Path

import pytest
from scrapy import Request
from scrapy.http import HtmlResponse

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "ande_convocatorias_v1.html"
SPIDER = (
    Path(__file__).resolve().parents[1]
    / "worker"
    / "scraping"
    / "spiders"
    / "Convocatorias"
    / "fondosspyder.py"
)


def cargar_spider():
    spec = importlib.util.spec_from_file_location("fondosspyder", SPIDER)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def spider_mod():
    return cargar_spider()


def test_html_local_lee_las_tarjetas_del_fixture(spider_mod):
    html = FIXTURE.read_text(encoding="utf-8")
    # Valores tomados del fixture, no del parser: cada tarjeta trae estos tres nodos.
    nombres = re.findall(r'<div class="uk-margin name">(.*?)</div>', html)
    estados = re.findall(r'<div class="uk-margin estado">(.*?)</div>', html)
    hrefs = re.findall(r'<a class="uk-position-cover" href="([^"]+)"', html)

    assert nombres
    assert len(nombres) == len(estados) == len(hrefs)

    items = spider_mod.parsear_html_local(FIXTURE)

    assert [(item["nombre"], item["estado"]) for item in items] == list(zip(nombres, estados))
    assert [item["link"] for item in items] == ["https://ande.org.uy" + href for href in hrefs]
    assert all(item["nombre"] and item["estado"] and item["link"] for item in items)
    # Primera tarjeta del fixture, para dejar el valor esperado escrito.
    assert items[0] == {
        "nombre": "Despega Uruguay",
        "estado": "Abierta",
        "link": "https://ande.org.uy/convocatorias/item/despega-uruguay.html?category_id=10",
    }


def test_el_listado_en_vivo_sigue_paginando(spider_mod):
    html = """
    <figure class="uk-overlay">
        <div class="uk-margin estado">Abierta</div>
        <div class="uk-margin name">Ejemplo</div>
        <a class="uk-position-cover" href="/convocatorias/item/ejemplo.html"></a>
    </figure>
    <a class="next" href="/convocatorias/2.html"></a>
    """
    response = HtmlResponse(
        url=spider_mod.URL_LISTADO,
        body=html.encode(),
        encoding="utf-8",
    )

    resultados = list(spider_mod.FondosSpyder().parse(response))

    assert resultados[0]["nombre"] == "Ejemplo"
    pedido = resultados[1]
    assert isinstance(pedido, Request)
    assert pedido.url == "https://ande.org.uy/convocatorias/2.html"


def test_sin_archivo_local_el_arranque_sigue_siendo_el_sitio(spider_mod):
    pedidos = asyncio.run(_arranque(spider_mod.FondosSpyder()))

    assert len(pedidos) == 1
    assert isinstance(pedidos[0], Request)
    assert pedidos[0].url == spider_mod.URL_LISTADO


def test_arranque_con_html_local_no_pide_la_red(spider_mod):
    spider = spider_mod.FondosSpyder(html_local=str(FIXTURE))
    items = asyncio.run(_arranque(spider))

    assert items
    assert all(isinstance(item, dict) for item in items)
    assert items[0]["nombre"] == "Despega Uruguay"


async def _arranque(spider):
    return [item async for item in spider.start()]


def test_html_local_no_arma_el_pedido_de_la_pagina_siguiente(spider_mod):
    items = spider_mod.parsear_html_local(FIXTURE)

    assert items
    assert all(not isinstance(item, Request) for item in items)
