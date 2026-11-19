"""Carga formularios_ande.json en formularios y formularios_campos.

formularios es una fila por convocatoria. formularios_campos son sus campos,
unidos por formulario_id. Cada campo trae sección, tipo, opciones y selector.
Volver a correrlo reemplaza esas convocatorias.

Desde Backend/:

    python worker/scraping/procesamiento/cargar_formularios.py
"""

import json
import os
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
                    ALTER COLUMN selector SET NOT NULL
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


if __name__ == "__main__":
    cargar()
