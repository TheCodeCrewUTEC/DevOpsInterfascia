import json
from pathlib import Path

from docling.document_converter import DocumentConverter


def procesar_archivo(
    converter: DocumentConverter,
    ruta: Path
):

    print(
        f"[DOCLING] Procesando: {ruta.name}"
    )

    resultado = converter.convert(
        str(ruta)
    )

    # DOCUMENTO ESTRUCTURADO DE DOCLING
    documento = resultado.document

    # MARKDOWN
    texto = documento.export_to_markdown()

    return {
        "nombre": ruta.name,
        "ruta": str(ruta),
        "texto": texto,

        # DoclingDocument queda en memoria.
        # NO se guarda en el JSON.
        "documento": documento
    }


def procesar_job(
    carpeta_job: Path
):

    print(
        f"[DOCLING] Procesando carpeta: {carpeta_job}"
    )

    converter = DocumentConverter()

    archivos = [
        archivo
        for archivo in carpeta_job.iterdir()
        if archivo.is_file()
        and archivo.name != "resultado_docling.json"
    ]

    resultados = []

    for archivo in archivos:

        resultado = procesar_archivo(
            converter,
            archivo
        )

        resultados.append(resultado)

    # GUARDAR RESULTADO EN JSON
    resultado_path = (
        carpeta_job / "resultado_docling.json"
    )

    datos_json = {
        "archivos": [
            {
                "nombre": resultado["nombre"],
                "ruta": resultado["ruta"],
                "texto": resultado["texto"]
            }
            for resultado in resultados
        ]
    }

    with resultado_path.open(
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            datos_json,
            archivo,
            ensure_ascii=False,
            indent=4
        )

    print(
        f"[DOCLING] Resultado guardado en: "
        f"{resultado_path}"
    )

    return resultados