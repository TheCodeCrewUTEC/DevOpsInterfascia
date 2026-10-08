import json
import scrapy


class SpiderPDF(scrapy.Spider):
    name = "SpiderPDF"

    async def start(self):

        with open(
            "FondosInversores.json",
            encoding="utf-8"
        ) as f:

            fondos = json.load(f)

        print("Fondos:", len(fondos))

        for fondo in fondos:

            yield scrapy.Request(
                fondo["link"],
                callback=self.parse_fondo,
                meta=fondo
            )

    def parse_fondo(self, response):

        documentos = []

        for href in response.css("a::attr(href)").getall():

            href = response.urljoin(href)

            if href.lower().endswith(
                (".pdf", ".doc", ".docx")
            ):
                documentos.append(href)

        yield {
            "nombre": response.meta["nombre"],
            "estado": response.meta["estado"],
            "link": response.meta["link"],
            "documentos": documentos
        }