"""Dígito verificador de la cédula y del RUT uruguayos.

La IA propone el número. Esta fórmula decide si cierra: no es un cálculo
que convenga dejarle al modelo.
"""

import json
import re
import unicodedata


def plano(texto: str) -> str:
    base = unicodedata.normalize("NFD", texto or "")
    sin_acentos = "".join(caracter for caracter in base if unicodedata.category(caracter) != "Mn")
    return " ".join(sin_acentos.lower().replace("*", " ").replace("_", " ").split())


def digitos(valor) -> str:
    return "".join(caracter for caracter in str(valor or "") if caracter.isdigit())


def cedula_valida(valor) -> bool:
    """Cédula uruguaya: hasta 7 dígitos más el verificador.

    Coeficientes 2, 9, 8, 7, 6, 3, 4 sobre los primeros siete, con ceros a la
    izquierda. El verificador es (10 - suma % 10) % 10.
    """
    numero = digitos(valor)
    if len(numero) not in (7, 8):
        return False
    numero = numero.zfill(8)
    factores = (2, 9, 8, 7, 6, 3, 4)
    suma = sum(int(numero[indice]) * factores[indice] for indice in range(7))
    verificador = (10 - (suma % 10)) % 10
    return verificador == int(numero[7])


def rut_valido(valor) -> bool:
    """RUT uruguayo: 12 dígitos, con la forma XX######001 más el verificador.

    Los dos primeros van de 01 a 22, los seis siguientes no son todos cero
    y después viene 001. Coeficientes 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2 sobre
    los primeros once. Si el resto de dividir por 11 es 0, el verificador
    es 0. Si es 1, el número no existe. En otro caso es 11 menos el resto.
    """
    numero = digitos(valor)
    if len(numero) != 12:
        return False
    if not ("01" <= numero[:2] <= "22"):
        return False
    if numero[2:8] == "000000" or numero[8:11] != "001":
        return False
    factores = (4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    suma = sum(int(numero[indice]) * factores[indice] for indice in range(11))
    resto = suma % 11
    if resto == 1:
        return False
    verificador = 0 if resto == 0 else 11 - resto
    return verificador == int(numero[11])


def es_nombre(etiqueta: str) -> bool:
    nombre = plano(etiqueta)
    if clase_identificador(etiqueta):
        return False
    return "razon social" in nombre or "nombre" in nombre


def instruccion_nombre(etiqueta: str) -> str:
    if not es_nombre(etiqueta):
        return ""
    return (
        "Es un nombre o una razón social. Devolvé solo ese texto, "
        "tal como figura en los documentos. "
        "No devuelvas un RUT, una cédula ni ningún otro número, "
        "aunque el subtítulo hable del RUT o del documento."
    )


def limpiar_respuesta_nombre(etiqueta: str, respuesta):
    """Un nombre no puede quedar en un número pelado."""
    if not isinstance(respuesta, str) or not es_nombre(etiqueta):
        return respuesta
    texto = respuesta.strip()
    if texto and not re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", texto):
        return None
    return respuesta


def instruccion_formato(etiqueta: str) -> str:
    """Texto para el prompt cuando el campo es un RUT o un documento."""
    clase = clase_identificador(etiqueta)
    if clase == "rut":
        return (
            "Es un RUT uruguayo, un número de 12 dígitos con la forma "
            "XX######001 y un dígito verificador, por ejemplo 21-100342-001-7. "
            "Devolvé solo ese número, tal como figura en los documentos, o null. "
            "No devuelvas una oración, un plazo ni una descripción."
        )
    if clase in {"cedula", "documento"}:
        return (
            "Es un número de documento de identidad. Si es una cédula uruguaya, "
            "son 7 u 8 dígitos, con o sin puntos y guión, por ejemplo 1.234.567-2. "
            "Devolvé solo ese número, tal como figura en los documentos, o null. "
            "No devuelvas una oración, un plazo ni una descripción."
        )
    return ""


def clase_identificador(etiqueta: str) -> str | None:
    nombre = plano(etiqueta)
    if re.search(r"\brut\b", nombre):
        return "rut"
    if "cedula" in nombre:
        return "cedula"
    if (
        "documento de identidad" in nombre
        or "numero de documento" in nombre
        or "nro de documento" in nombre
    ):
        return "documento"
    return None


def es_tipo_documento(etiqueta: str) -> bool:
    return plano(etiqueta).startswith("tipo de documento")


def es_pais_documento(etiqueta: str) -> bool:
    return "pais de documento" in plano(etiqueta)


def _mensaje_rut(valor) -> str | None:
    numero = digitos(valor)
    if not numero:
        return None
    if not rut_valido(valor):
        return "el RUT no es válido."
    return None


def _mensaje_cedula(valor) -> str | None:
    numero = digitos(valor)
    if not numero:
        return None
    if not cedula_valida(valor):
        return "la cédula no es válida."
    return None


def _aplica_cedula(tipo: str | None, pais: str | None) -> bool:
    if tipo is not None and "cedula" not in plano(tipo):
        return False
    if pais is not None and pais.strip() and "uruguay" not in plano(pais):
        return False
    return True


def mensaje_de_valor(clase: str, valor, tipo: str | None, pais: str | None) -> str | None:
    if clase == "rut":
        return _mensaje_rut(valor)
    if clase == "cedula":
        if pais is not None and pais.strip() and "uruguay" not in plano(pais):
            return None
        return _mensaje_cedula(valor)
    if clase == "documento" and _aplica_cedula(tipo, pais):
        return _mensaje_cedula(valor)
    return None


def _filas(respuesta) -> list[dict]:
    datos = respuesta
    if isinstance(datos, str):
        texto = datos.strip()
        if not texto:
            return []
        try:
            datos = json.loads(texto)
        except json.JSONDecodeError:
            return []
    if isinstance(datos, dict):
        datos = [datos]
    if not isinstance(datos, list):
        return []
    return [fila for fila in datos if isinstance(fila, dict)]


def _celda(fila: dict, columnas: list[dict], coincide) -> str | None:
    for columna in columnas:
        if coincide(str(columna.get("etiqueta") or "")):
            return str(fila.get(columna.get("etiqueta")) or "")
    return None


def _hermano(campos, campo, por_selector, coincide) -> str | None:
    seccion = str(campo.get("seccion") or "").strip()
    if not seccion:
        return None
    for otro in campos:
        if otro is campo or otro.get("columnas"):
            continue
        if otro.get("seccion") != seccion:
            continue
        if not coincide(str(otro.get("campo") or "")):
            continue
        selector = otro.get("selector")
        return str(por_selector.get(selector) or "") if selector else ""
    return None


def mensajes_del_campo(campo, respuesta, por_selector, campos) -> list[str]:
    """Avisos para un campo ya respondido. Vacío si el número cierra o no aplica."""
    etiqueta = str(campo.get("campo") or "")
    columnas = campo.get("columnas") or []
    if columnas:
        titulo = etiqueta.replace("*", "").strip()
        avisos = []
        for indice, fila in enumerate(_filas(respuesta), start=1):
            tipo = _celda(fila, columnas, es_tipo_documento)
            pais = _celda(fila, columnas, es_pais_documento)
            for columna in columnas:
                nombre = str(columna.get("etiqueta") or "")
                clase = clase_identificador(nombre)
                if not clase:
                    continue
                mensaje = mensaje_de_valor(clase, fila.get(nombre), tipo, pais)
                if mensaje:
                    avisos.append(f"{titulo}, fila {indice}, {nombre.replace('*', '').strip()}: {mensaje}")
        return avisos

    clase = clase_identificador(etiqueta)
    if not clase:
        return []
    tipo = _hermano(campos, campo, por_selector, es_tipo_documento)
    pais = _hermano(campos, campo, por_selector, es_pais_documento)
    mensaje = mensaje_de_valor(clase, respuesta, tipo, pais)
    if not mensaje:
        return []
    return [f"{etiqueta.replace('*', '').strip()}: {mensaje}"]
