from app.services.documento_uy import (
    cedula_valida,
    es_nombre,
    instruccion_formato,
    instruccion_nombre,
    limpiar_respuesta_nombre,
    mensajes_del_campo,
    rut_valido,
)


def test_un_nombre_no_queda_en_un_numero():
    assert es_nombre("Nombre de la empresa *")
    assert es_nombre("Razón Social *")
    assert not es_nombre("RUT *")
    assert not es_nombre("Número de documento *")
    assert "razón social" in instruccion_nombre("Nombre de la empresa *")
    assert limpiar_respuesta_nombre("Razón Social *", "211003420017") is None
    assert limpiar_respuesta_nombre("Razón Social *", "21-100342-001-7") is None
    assert limpiar_respuesta_nombre("Nombre de la empresa *", "La Popeta S.A.") == "La Popeta S.A."


def test_el_prompt_pide_el_numero_y_no_una_oracion():
    rut = instruccion_formato("RUT *")
    documento = instruccion_formato("Número de documento *")
    assert "12 dígitos" in rut
    assert "21-100342-001-7" in rut
    assert "1.234.567-2" in documento
    assert "oración" in documento
    assert instruccion_formato("Teléfono *") == ""


def test_cedula_acepta_el_digito_y_el_formato_con_puntos():
    assert cedula_valida("12345672")
    assert cedula_valida("1.234.567-2")
    assert not cedula_valida("12345673")
    assert not cedula_valida("1234567")
    assert not cedula_valida("")


def test_rut_acepta_doce_digitos_con_verificador():
    assert rut_valido("211003420017")
    assert rut_valido("21-100342-001-7")
    assert rut_valido("211406340011")
    assert not rut_valido("210303670014")
    assert not rut_valido("123456789010")
    assert not rut_valido("21000000001")


def test_avisa_rut_y_cedula_por_el_nombre_del_campo():
    campos = [
        {"campo": "RUT *", "selector": "rutEmpresa", "seccion": "Empresa", "columnas": []},
        {"campo": "Cédula de Identidad *", "selector": "ci", "seccion": "Persona", "columnas": []},
        {"campo": "Teléfono *", "selector": "tel", "seccion": "Empresa", "columnas": []},
    ]
    valores = {"rutEmpresa": "210303670014", "ci": "1.234.567-3", "tel": "099123456"}

    assert mensajes_del_campo(campos[0], valores["rutEmpresa"], valores, campos) == [
        "RUT: el RUT no es válido."
    ]
    assert mensajes_del_campo(campos[1], valores["ci"], valores, campos) == [
        "Cédula de Identidad: la cédula no es válida."
    ]
    assert mensajes_del_campo(campos[2], valores["tel"], valores, campos) == []
    assert mensajes_del_campo(campos[0], "21-100342-001-7", valores, campos) == []


def test_documento_solo_se_valida_como_cedula_uruguaya():
    campos = [
        {"campo": "Tipo de documento *", "selector": "tipo", "seccion": "Persona", "columnas": []},
        {"campo": "Número de documento *", "selector": "nro", "seccion": "Persona", "columnas": []},
        {"campo": "País de documento *", "selector": "pais", "seccion": "Persona", "columnas": []},
    ]
    numero = campos[1]

    uruguay = {"tipo": "Cédula de Identidad", "nro": "12345673", "pais": "Uruguay (UY)"}
    assert mensajes_del_campo(numero, uruguay["nro"], uruguay, campos) == [
        "Número de documento: la cédula no es válida."
    ]

    otro = {"tipo": "Otro", "nro": "12345673", "pais": "Uruguay (UY)"}
    assert mensajes_del_campo(numero, otro["nro"], otro, campos) == []

    extranjero = {"tipo": "Cédula de Identidad", "nro": "12345673", "pais": "Argentina (AR)"}
    assert mensajes_del_campo(numero, extranjero["nro"], extranjero, campos) == []

    valida = {"tipo": "Cédula de Identidad", "nro": "12345672", "pais": "Uruguay (UY)"}
    assert mensajes_del_campo(numero, valida["nro"], valida, campos) == []


def test_tabla_marca_la_fila_del_titular():
    campo = {
        "campo": "Titulares *",
        "selector": "tabla:n1",
        "seccion": "Titulares",
        "columnas": [
            {"etiqueta": "Tipo de documento *"},
            {"etiqueta": "Número de documento de identidad *"},
            {"etiqueta": "País de documento *"},
            {"etiqueta": "Nombre *"},
        ],
    }
    filas = [
        {
            "Tipo de documento *": "Cédula de Identidad",
            "Número de documento de identidad *": "12345673",
            "País de documento *": "Uruguay (UY)",
            "Nombre *": "Ana",
        }
    ]

    assert mensajes_del_campo(campo, filas, {}, [campo]) == [
        "Titulares, fila 1, Número de documento de identidad: la cédula no es válida."
    ]
