"""RF002: una segunda ingesta cambia la fecha de cierre y RF005 registra el evento.

El listado identifica la convocatoria (nombre, estado, URL). La fecha sale del
período escrito en el documento, con periodo_en_bd. La primera versión está en
ande_documento_v1.txt. La segunda está en ande_convocatorias_v2.html, en la
tarjeta de Despega Uruguay. El aviso lo escribe revisar_convocatorias en
notificacion; no se inserta a mano.
"""

import json

import pytest

from app.services import deteccion_alertas_service as deteccion
from test_extraccion_convocatorias import (
    EXTRACTOR,
    FIXTURE_DOCUMENTO,
    FIXTURE_LISTADO,
    REQUISITOS,
    SPIDER,
    asegurar_esquema,
    cargar_modulo,
    conectar,
)

FIXTURE_LISTADO_V2 = FIXTURE_LISTADO.with_name("ande_convocatorias_v2.html")
SUSCRIPTOR = "prueba-rf002"


def asegurar_alertas(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS suscripcion (
                id SERIAL PRIMARY KEY,
                usuario_sub TEXT NOT NULL,
                tipo TEXT NOT NULL CHECK (tipo IN ('convocatoria', 'institucion', 'tematica')),
                convocatoria_id INTEGER,
                valor TEXT,
                creado TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS suscripcion_unica
                ON suscripcion (
                    usuario_sub, tipo, COALESCE(convocatoria_id, 0), COALESCE(lower(valor), '')
                )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS preferencia_notificacion (
                usuario_sub TEXT PRIMARY KEY,
                alerta_apertura BOOLEAN NOT NULL DEFAULT TRUE,
                alerta_cierre BOOLEAN NOT NULL DEFAULT TRUE,
                alerta_actualizacion BOOLEAN NOT NULL DEFAULT TRUE,
                dias_anticipacion_cierre INTEGER NOT NULL DEFAULT 7
                    CHECK (dias_anticipacion_cierre BETWEEN 1 AND 60),
                email_habilitado BOOLEAN NOT NULL DEFAULT FALSE,
                email_habilitado_desde TIMESTAMPTZ,
                email TEXT,
                creado TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                actualizado TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS notificacion (
                id SERIAL PRIMARY KEY,
                usuario_sub TEXT NOT NULL,
                tipo TEXT NOT NULL CHECK (tipo IN ('apertura', 'cierre', 'actualizacion')),
                convocatoria_id INTEGER,
                titulo TEXT NOT NULL,
                mensaje TEXT NOT NULL,
                detalle JSONB,
                clave_dedup TEXT NOT NULL,
                leida BOOLEAN NOT NULL DEFAULT FALSE,
                eliminada BOOLEAN NOT NULL DEFAULT FALSE,
                creado TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                email_enviado_en TIMESTAMPTZ,
                email_intentos INTEGER NOT NULL DEFAULT 0,
                email_error TEXT,
                UNIQUE (usuario_sub, clave_dedup)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS convocatoria_seguimiento (
                convocatoria_id INTEGER PRIMARY KEY,
                datos JSONB NOT NULL,
                apertura_notificada BOOLEAN NOT NULL DEFAULT FALSE,
                actualizado TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    conn.commit()


def cierre_escrito(extractor, texto):
    coincidencia = extractor._PERIODO.search(texto)
    assert coincidencia and coincidencia.group(4), texto
    return extractor._fecha_escrita(
        coincidencia.group(4),
        coincidencia.group(5),
        coincidencia.group(6),
    ), coincidencia.group(0)


def fila_de(cur, convocatoria_id):
    cur.execute(
        """
        SELECT id, titulo, estado, institucion, fecha_apertura, fecha_cierre,
               descripcion, beneficiarios, requisitos, financiamiento
        FROM convocatoria
        WHERE id = %s
        """,
        (convocatoria_id,),
    )
    return cur.fetchone()


def buscar_o_crear(cur, listado):
    cur.execute(
        """
        SELECT id
        FROM convocatoria
        WHERE titulo = %s
        ORDER BY id
        LIMIT 1
        """,
        (listado["nombre"],),
    )
    encontrada = cur.fetchone()
    if encontrada:
        return encontrada[0]

    cur.execute(
        """
        INSERT INTO convocatoria (
            titulo, institucion, estado, descripcion, beneficiarios, requisitos, fuente
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            listado["nombre"],
            "Agencia Nacional de Desarrollo (ANDE)",
            listado["estado"],
            "Objetivo ya cargado para no consultar al modelo.",
            "Beneficiarios ya cargados para no consultar al modelo.",
            REQUISITOS,
            listado["link"],
        ),
    )
    return cur.fetchone()[0]


def reemplazar_texto(cur, convocatoria_id, texto, listado):
    cur.execute(
        """
        SELECT id
        FROM documento
        WHERE convocatoria_id = %s
        ORDER BY id
        LIMIT 1
        """,
        (convocatoria_id,),
    )
    documento = cur.fetchone()
    if documento:
        documento_id = documento[0]
    else:
        cur.execute(
            """
            INSERT INTO documento (convocatoria_id, nombre, url)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (convocatoria_id, "ande_documento_v1.txt", listado["link"]),
        )
        documento_id = cur.fetchone()[0]

    cur.execute(
        """
        DELETE FROM chunk
        WHERE documento_id IN (
            SELECT id FROM documento WHERE convocatoria_id = %s
        )
        """,
        (convocatoria_id,),
    )
    cur.execute(
        """
        INSERT INTO chunk (documento_id, contenido, pagina)
        VALUES (%s, %s, 1)
        """,
        (documento_id, texto),
    )


def ingerir(cur, extractor, listado, texto):
    convocatoria_id = buscar_o_crear(cur, listado)
    reemplazar_texto(cur, convocatoria_id, texto, listado)
    extractor.procesar_convocatoria(cur, fila_de(cur, convocatoria_id))
    return convocatoria_id


def suscribir(cur, convocatoria_id):
    cur.execute(
        """
        SELECT id
        FROM suscripcion
        WHERE usuario_sub = %s AND tipo = 'convocatoria' AND convocatoria_id = %s
        """,
        (SUSCRIPTOR, convocatoria_id),
    )
    if cur.fetchone():
        return
    cur.execute(
        """
        INSERT INTO suscripcion (usuario_sub, tipo, convocatoria_id)
        VALUES (%s, 'convocatoria', %s)
        """,
        (SUSCRIPTOR, convocatoria_id),
    )


def detalle_de(valor):
    if isinstance(valor, str):
        return json.loads(valor)
    return valor


def test_la_segunda_ingesta_actualiza_el_cierre_y_deja_el_evento(monkeypatch):
    monkeypatch.setattr(deteccion, "get_connection", conectar)
    extractor = cargar_modulo(EXTRACTOR, "extraer_convocatorias_cierre")
    monkeypatch.setattr(
        extractor,
        "consultar_qwen",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("la prueba no debe consultar a Qwen")
        ),
    )

    texto_v1 = FIXTURE_DOCUMENTO.read_text(encoding="utf-8")
    html_v2 = FIXTURE_LISTADO_V2.read_text(encoding="utf-8")
    cierre_v1, _ = cierre_escrito(extractor, texto_v1)
    cierre_v2, frase_v2 = cierre_escrito(extractor, html_v2)
    assert cierre_v1 != cierre_v2

    listado = cargar_modulo(SPIDER, "fondosspyder_cierre")
    tarjeta_v1 = listado.parsear_html_local(FIXTURE_LISTADO)[0]
    tarjeta_v2 = listado.parsear_html_local(FIXTURE_LISTADO_V2)[0]
    assert tarjeta_v1["nombre"] == tarjeta_v2["nombre"] == "Despega Uruguay"
    assert tarjeta_v1["link"] == tarjeta_v2["link"]

    try:
        conn = conectar()
    except Exception as error:
        pytest.fail(
            "No hay base de prueba en 127.0.0.1:5434. "
            "Levantala con: docker compose --env-file .env.test "
            f"-f docker-compose.test.yml up -d\n{error}"
        )

    try:
        asegurar_esquema(conn)
        asegurar_alertas(conn)

        with conn.cursor() as cur:
            convocatoria_id = ingerir(cur, extractor, tarjeta_v1, texto_v1)
            titulo, estado, fuente, cierre, cantidad = _leida(cur, convocatoria_id)
        conn.commit()

        assert titulo == "Despega Uruguay"
        assert estado == "Abierta"
        assert fuente == tarjeta_v1["link"]
        assert cierre == cierre_v1
        assert cantidad == 1

        with conn.cursor() as cur:
            suscribir(cur, convocatoria_id)
        conn.commit()
        deteccion.revisar_convocatorias()

        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM notificacion WHERE usuario_sub = %s",
                (SUSCRIPTOR,),
            )
            ingerir(cur, extractor, tarjeta_v2, frase_v2)
            mismo_id, titulo, estado, fuente, cierre, cantidad = _estado(cur, tarjeta_v1["nombre"])
        conn.commit()

        assert mismo_id == convocatoria_id
        assert titulo == "Despega Uruguay"
        assert estado == "Abierta"
        assert fuente == tarjeta_v1["link"]
        assert cierre == cierre_v2
        assert cantidad == 1

        resultado = deteccion.revisar_convocatorias()
        assert resultado["actualizaciones"] == 1

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT usuario_sub, tipo, convocatoria_id, titulo, mensaje, detalle
                FROM notificacion
                WHERE convocatoria_id = %s AND tipo = 'actualizacion'
                ORDER BY id DESC
                LIMIT 1
                """,
                (convocatoria_id,),
            )
            aviso = cur.fetchone()
            cur.execute(
                """
                SELECT count(*)
                FROM notificacion
                WHERE convocatoria_id = %s AND tipo = 'actualizacion'
                """,
                (convocatoria_id,),
            )
            avisos = cur.fetchone()[0]
    finally:
        conn.close()

    assert avisos == 1
    usuario, tipo, aviso_id, titulo_aviso, mensaje, detalle = aviso
    cambios = detalle_de(detalle)
    assert usuario == SUSCRIPTOR
    assert tipo == "actualizacion"
    assert aviso_id == convocatoria_id
    assert titulo_aviso == "Actualización en Despega Uruguay"
    assert cambios == [
        {
            "campo": "fecha_cierre",
            "antes": cierre_v1.isoformat(),
            "despues": cierre_v2.isoformat(),
        }
    ]
    assert "Fecha de cierre" in mensaje
    assert cierre_v1.strftime("%d/%m/%Y") in mensaje
    assert cierre_v2.strftime("%d/%m/%Y") in mensaje


def _leida(cur, convocatoria_id):
    cur.execute(
        """
        SELECT titulo, estado, fuente, fecha_cierre,
               (SELECT count(*) FROM convocatoria WHERE titulo = c.titulo)
        FROM convocatoria c
        WHERE c.id = %s
        """,
        (convocatoria_id,),
    )
    return cur.fetchone()


def _estado(cur, titulo):
    cur.execute(
        """
        SELECT id, titulo, estado, fuente, fecha_cierre, count(*) OVER ()
        FROM convocatoria
        WHERE titulo = %s
        ORDER BY id
        """,
        (titulo,),
    )
    filas = cur.fetchall()
    assert len(filas) == 1
    return filas[0]
