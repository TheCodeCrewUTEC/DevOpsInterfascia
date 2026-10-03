import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )


def ensure_schema():
    conn = get_connection()

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