from pathlib import Path

import scrapy
from scrapy.http import HtmlResponse

# Misma página que usa el spider en producción. Sirve de URL base al leer un HTML
# local, para que los links queden absolutos igual que en el sitio.
URL_LISTADO = "https://ande.org.uy/convocatorias/advanced-search/1938.html"


def convocatorias_de(response):
    """Tarjetas de una página del listado de ANDE.

    La usa el spider en vivo y la lectura de un HTML local: un solo parser.
    """

    for fondos in response.css("figure.uk-overlay"):
        yield {
            "nombre": fondos.css("div.uk-margin.name::text").get(),
            "estado": fondos.css("div.uk-margin.estado::text").get(),
            "link": response.urljoin(
                fondos.css("a.uk-position-cover::attr(href)").get()
            ),
        }


def parsear_html_local(ruta, url_base=URL_LISTADO):
    """Lee un HTML guardado y devuelve las convocatorias de esa página.

    No sigue el enlace a la página siguiente y no abre la red.
    """

    response = HtmlResponse(
        url=url_base,
        body=Path(ruta).read_bytes(),
        encoding="utf-8",
    )
    return list(convocatorias_de(response))


class FondosSpyder(scrapy.Spider):
    name = "FondoInversor"
    start_urls = [URL_LISTADO]

    custom_settings = {
        "USER_AGENT": (
            "InterfasciaBot/1.0 "
            "(plataforma de innovación y vigilancia tecnológica)"
        ),
    }

    def __init__(self, html_local=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo para pruebas: scrapy runspider fondosspyder.py -a html_local=archivo.html
        self.html_local = html_local

    async def start(self):
        if self.html_local:
            for convocatoria in parsear_html_local(self.html_local):
                yield convocatoria
            return

        async for pedido in super().start():
            yield pedido

    def parse(self, response):
        self.logger.info(
            "Página recibida: %s | HTTP %s",
            response.url,
            response.status,
        )

        yield from convocatorias_de(response)

        siguiente = response.css("a.next::attr(href)").get()

        if siguiente:
            yield response.follow(siguiente, callback=self.parse)
