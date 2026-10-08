import json
import scrapy
from pathlib import Path
from docling.document_converter import DocumentConverter


class SpiderDocumentos(scrapy.Spider):
    name = "SpiderDocumentos"

    def __init__(self):
        self.converter = DocumentConverter()

    async def start(self):

        with open(
            "FondosConDocumentos.json",
            encoding="utf-8"
        ) as f:

            fondos = json.load(f)

        for fondo in fondos:

            for documento in fondo["documentos"]:

                yield scrapy.Request(
                    documento,
                    callback=self.parse_documento,
                    meta={
                        "nombre": fondo["nombre"],
                        "estado": fondo["estado"],
                        "link": fondo["link"]
                    }
                )

    def parse_documento(self, response):

        try:

            # Guardar temporalmente el documento
            extension = Path(response.url).suffix or ".pdf"

            archivo_temporal = (
                Path("temp_documento") / f"documento{extension}"
            )

            archivo_temporal.parent.mkdir(
                exist_ok=True
            )

            archivo_temporal.write_bytes(response.body)

            # Procesar con Docling
            resultado = self.converter.convert(
                str(archivo_temporal)
            )

            # Convertir a Markdown
            texto = resultado.document.export_to_markdown()

            yield {
                "nombre": response.meta["nombre"],
                "estado": response.meta["estado"],
                "link_fondo": response.meta["link"],
                "documento": response.url,
                "texto": texto
            }

        except Exception as e:

            yield {
                "nombre": response.meta["nombre"],
                "documento": response.url,
                "error": str(e)
            }