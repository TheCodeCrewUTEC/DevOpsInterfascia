import os
import time

import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    port = os.getenv("DB_PORT")
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=int(port) if port else None,
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


def ensure_schema():
    conn = None
    ultimo_error = None

    for intento in range(1, 11):
        try:
            conn = get_connection()
            break
        except psycopg2.OperationalError as error:
            ultimo_error = error
            print(f"[DB] Intento {intento}/10 falló: {error}")
            time.sleep(3)

    if conn is None:
        raise ultimo_error

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS formulario_job (
                    id SERIAL PRIMARY KEY,
                    estado TEXT NOT NULL,
                    formulario_path TEXT,
                    creado TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    iniciado TIMESTAMPTZ,
                    finalizado TIMESTAMPTZ,
                    resultado_path TEXT,
                    error TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS respuesta_formulario (
                    id SERIAL PRIMARY KEY,
                    job_id INTEGER NOT NULL REFERENCES formulario_job(id),
                    campo TEXT NOT NULL,
                    respuesta TEXT,
                    fuentes TEXT
                )
                """
            )
        conn.commit()
    finally:
        conn.close()