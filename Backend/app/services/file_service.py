import re
import unicodedata
from pathlib import Path

EXTENSIONES_PERMITIDAS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".xls",
    ".txt",
}

def validar_extension(nombre: str) -> bool:
    extension = Path(nombre).suffix.lower()

    return extension in EXTENSIONES_PERMITIDAS

def sanitizar_nombre_archivo(nombre: str) -> str:
    """
    Sanitiza el nombre de un archivo recibido desde el cliente.

    Ejemplo:
        "Formulario de Postulación (2026).pdf"
        -> "Formulario_de_Postulacion_2026.pdf"
    """

    nombre = Path(nombre).name
    nombre_base = Path(nombre).stem
    extension = Path(nombre).suffix.lower()

    # Normalizar caracteres Unicode
    nombre_base = unicodedata.normalize(
        "NFKD",
        nombre_base
    )

    # Eliminar acentos
    nombre_base = "".join(
        caracter
        for caracter in nombre_base
        if not unicodedata.combining(caracter)
    )

    # Reemplazar caracteres no permitidos
    nombre_base = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        nombre_base
    )

    # Eliminar "_" repetidos
    nombre_base = re.sub(
        r"_+",
        "_",
        nombre_base
    )

    # Eliminar "_" al principio/final
    nombre_base = nombre_base.strip("_")


    if not nombre_base:
        nombre_base = "archivo"

    return f"{nombre_base}{extension}"