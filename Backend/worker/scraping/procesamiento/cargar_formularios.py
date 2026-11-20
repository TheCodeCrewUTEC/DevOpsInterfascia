"""Carga formularios_ande.json en formularios y formularios_campos.

formularios es una fila por convocatoria. formularios_campos son sus campos,
unidos por formulario_id. Cada campo trae sección, tipo, opciones y selector.
Volver a correrlo reemplaza esas convocatorias.

Desde Backend/:

    python worker/scraping/procesamiento/cargar_formularios.py
"""

import json
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json, execute_values

BACKEND = Path(__file__).resolve().parents[3]
JSON_FORMULARIOS = (
    BACKEND / "worker" / "scraping" / "salida" / "formularios_ande.json"
)

load_dotenv(BACKEND / ".env")
load_dotenv(BACKEND.parent / ".env")


def _filas(datos):
    filas = []
    for item in datos.get("formularios", []):
        convocatoria = " ".join((item.get("convocatoria") or "").split())
        formulario = item.get("formulario") or {}
        campos = formulario.get("campos") or []
        if not convocatoria or not campos:
            continue
        orden = 0
        for campo in campos:
            if isinstance(campo, str):
                etiqueta = " ".join(campo.split())
                seccion, tipo, opciones, selector = "General", "text", [], ""
                requerido = etiqueta.endswith("*")
            else:
                etiqueta = " ".join(str(campo.get("etiqueta") or "").split())
                seccion = " ".join(str(campo.get("seccion") or "General").split())
                tipo = " ".join(str(campo.get("tipo") or "text").split())
                opciones = campo.get("opciones") or []
                selector = " ".join(str(campo.get("selector") or "").split())
                requerido = bool(campo.get("requerido"))
            if not etiqueta or etiqueta == "*" or not selector:
                continue
            orden += 1
            filas.append(
                (
                    convocatoria,
                    orden,
                    seccion,
                    etiqueta,
                    tipo,
                    requerido,
                    Json(opciones),
                    selector,
                )
            )
    return filas


def cargar():
    datos = json.loads(JSON_FORMULARIOS.read_text(encoding="utf-8"))
    filas = _filas(datos)
    if not filas:
        raise SystemExit(f"No hay campos para cargar en {JSON_FORMULARIOS}")

    convocatorias = sorted({fila[0] for fila in filas})
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT_PUBLICADO", "5433")),
        dbname=os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "interfascia")),
        user=os.getenv("DB_USER", os.getenv("POSTGRES_USER", "interfascia")),
        password=os.getenv("DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "")),
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS formularios (
                    id SERIAL PRIMARY KEY,
                    convocatoria TEXT NOT NULL UNIQUE,
                    creado TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS formularios_campos (
                    id SERIAL PRIMARY KEY,
                    formulario_id INTEGER NOT NULL
                        REFERENCES formularios(id) ON DELETE CASCADE,
                    orden INTEGER NOT NULL,
                    seccion TEXT,
                    etiqueta TEXT NOT NULL,
                    tipo TEXT,
                    requerido BOOLEAN NOT NULL DEFAULT FALSE,
                    opciones JSONB NOT NULL DEFAULT '[]'::jsonb,
                    selector TEXT,
                    UNIQUE (formulario_id, orden)
                )
                """
            )
            cur.execute(
                "DELETE FROM formularios WHERE convocatoria = ANY(%s)",
                (convocatorias,),
            )
            ids = {}
            for convocatoria in convocatorias:
                cur.execute(
                    """
                    INSERT INTO formularios (convocatoria)
                    VALUES (%s)
                    RETURNING id
                    """,
                    (convocatoria,),
                )
                ids[convocatoria] = cur.fetchone()[0]
            execute_values(
                cur,
                """
                INSERT INTO formularios_campos (
                    formulario_id, orden, seccion, etiqueta, tipo,
                    requerido, opciones, selector
                )
                VALUES %s
                """,
                [
                    (ids[convocatoria], orden, seccion, etiqueta, tipo, requerido, opciones, selector)
                    for convocatoria, orden, seccion, etiqueta, tipo, requerido, opciones, selector in filas
                ],
            )
            cur.execute(
                """
                ALTER TABLE formularios_campos
                    ALTER COLUMN seccion SET NOT NULL,
                    ALTER COLUMN tipo SET NOT NULL,
                    ALTER COLUMN selector SET NOT NULL,
                    ADD COLUMN IF NOT EXISTS depende_de TEXT,
                    ADD COLUMN IF NOT EXISTS opciones_por_valor JSONB
                        NOT NULL DEFAULT '{}'::jsonb
                """
            )
        conn.commit()
    finally:
        conn.close()

    print(f"Convocatorias: {len(convocatorias)}")
    print(f"Campos: {len(filas)}")
    for convocatoria in convocatorias:
        cantidad = sum(1 for fila in filas if fila[0] == convocatoria)
        print(f"  {cantidad:3}  {convocatoria}")


def actualizar_dependencias():
    """Actualiza depende_de y opciones_por_valor sin borrar los formularios."""
    datos = json.loads(JSON_FORMULARIOS.read_text(encoding="utf-8"))
    cambios = []
    for item in datos.get("formularios", []):
        convocatoria = " ".join((item.get("convocatoria") or "").split())
        for campo in (item.get("formulario") or {}).get("campos") or []:
            if not isinstance(campo, dict) or not campo.get("depende_de"):
                continue
            selector = " ".join(str(campo.get("selector") or "").split())
            if not convocatoria or not selector:
                continue
            cambios.append(
                (
                    campo.get("depende_de"),
                    Json(campo.get("opciones_por_valor") or {}),
                    convocatoria,
                    selector,
                )
            )
    if not cambios:
        raise SystemExit(f"No hay listas dependientes en {JSON_FORMULARIOS}")

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT_PUBLICADO", "5433")),
        dbname=os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "interfascia")),
        user=os.getenv("DB_USER", os.getenv("POSTGRES_USER", "interfascia")),
        password=os.getenv("DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "")),
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                ALTER TABLE formularios_campos
                    ADD COLUMN IF NOT EXISTS depende_de TEXT,
                    ADD COLUMN IF NOT EXISTS opciones_por_valor JSONB
                        NOT NULL DEFAULT '{}'::jsonb
                """
            )
            actualizados = 0
            for depende_de, opciones_por_valor, convocatoria, selector in cambios:
                cur.execute(
                    """
                    UPDATE formularios_campos AS c
                    SET depende_de = %s,
                        opciones_por_valor = %s
                    FROM formularios AS f
                    WHERE f.id = c.formulario_id
                      AND f.convocatoria = %s
                      AND c.selector = %s
                    """,
                    (depende_de, opciones_por_valor, convocatoria, selector),
                )
                actualizados += cur.rowcount
        conn.commit()
    finally:
        conn.close()

    print(f"Campos dependientes en el JSON: {len(cambios)}")
    print(f"Filas actualizadas: {actualizados}")


def reemplazar_campos():
    """Reescribe los campos de cada formulario ya cargado, sin cambiar su id."""
    datos = json.loads(JSON_FORMULARIOS.read_text(encoding="utf-8"))
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT_PUBLICADO", "5433")),
        dbname=os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "interfascia")),
        user=os.getenv("DB_USER", os.getenv("POSTGRES_USER", "interfascia")),
        password=os.getenv("DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "")),
    )
    tablas = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                ALTER TABLE formularios_campos
                    ADD COLUMN IF NOT EXISTS columnas JSONB
                        NOT NULL DEFAULT '[]'::jsonb
                """
            )
            for item in datos.get("formularios", []):
                convocatoria = " ".join((item.get("convocatoria") or "").split())
                formulario = item.get("formulario") or {}
                campos = formulario.get("campos") or []
                if not convocatoria or not campos:
                    continue
                cur.execute(
                    "SELECT id FROM formularios WHERE convocatoria = %s",
                    (convocatoria,),
                )
                fila = cur.fetchone()
                if fila is None:
                    continue
                formulario_id = fila[0]
                cur.execute(
                    "DELETE FROM formularios_campos WHERE formulario_id = %s",
                    (formulario_id,),
                )
                orden = 0
                for campo in campos:
                    if not isinstance(campo, dict):
                        continue
                    etiqueta = " ".join(str(campo.get("etiqueta") or "").split())
                    selector = " ".join(str(campo.get("selector") or "").split())
                    if not etiqueta or not selector:
                        continue
                    orden += 1
                    if campo.get("tipo") == "tabla":
                        tablas += 1
                    cur.execute(
                        """
                        INSERT INTO formularios_campos (
                            formulario_id, orden, seccion, etiqueta, tipo,
                            requerido, opciones, selector, depende_de,
                            opciones_por_valor, columnas
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            formulario_id,
                            orden,
                            " ".join(str(campo.get("seccion") or "General").split()),
                            etiqueta,
                            " ".join(str(campo.get("tipo") or "text").split()),
                            bool(campo.get("requerido")),
                            Json(campo.get("opciones") or []),
                            selector,
                            campo.get("depende_de"),
                            Json(campo.get("opciones_por_valor") or {}),
                            Json(campo.get("columnas") or []),
                        ),
                    )
        conn.commit()
    finally:
        conn.close()
    print(f"Tablas: {tablas}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "dependencias":
        actualizar_dependencias()
    elif len(sys.argv) > 1 and sys.argv[1] == "campos":
        reemplazar_campos()
    else:
        cargar()
