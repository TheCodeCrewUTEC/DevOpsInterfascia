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
            # Formulario editable: tipo y página de cada campo, y la respuesta original
            # de la IA para saber qué corrigió el usuario. usuario_sub = dueño del job.
            cur.execute(
                """
                ALTER TABLE respuesta_formulario
                    ADD COLUMN IF NOT EXISTS tipo TEXT,
                    ADD COLUMN IF NOT EXISTS pagina INTEGER,
                    ADD COLUMN IF NOT EXISTS respuesta_ia TEXT,
                    ADD COLUMN IF NOT EXISTS editada BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
            # Respuestas anteriores a la columna: lo guardado es lo que propuso la IA
            cur.execute(
                """
                UPDATE respuesta_formulario
                SET respuesta_ia = respuesta
                WHERE respuesta_ia IS NULL
                  AND respuesta IS NOT NULL
                  AND NOT editada
                """
            )
            cur.execute(
                """
                ALTER TABLE formulario_job
                    ADD COLUMN IF NOT EXISTS usuario_sub TEXT,
                    ADD COLUMN IF NOT EXISTS consulta_token TEXT
                """
            )
            # Las consulta el Consultor IA; sin ellas /api/proyectos y /api/investigadores dan 500
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS proyectos (
                    id SERIAL PRIMARY KEY,
                    nombre TEXT,
                    estado TEXT,
                    anio TEXT,
                    descripcion TEXT,
                    investigadores TEXT,
                    creado TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS investigadores (
                    id SERIAL PRIMARY KEY,
                    nombre TEXT,
                    apellido TEXT,
                    institucion TEXT,
                    titulo TEXT,
                    investigaciones TEXT,
                    nivel_sni TEXT,
                    categoria_sni TEXT,
                    creado TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            # Copia de los datos del registro. Keycloak sigue manejando login y contraseñas;
            # el estado de aprobación se cambia desde la página de admin.
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    keycloak_id TEXT NOT NULL UNIQUE,
                    email TEXT,
                    nombre TEXT,
                    apellido TEXT,
                    celular TEXT,
                    departamento_residencia TEXT,
                    departamentos_actuacion TEXT[] NOT NULL DEFAULT '{}',
                    instituciones TEXT[] NOT NULL DEFAULT '{}',
                    perfil TEXT,
                    perfil_otro TEXT,
                    rol TEXT,
                    estado TEXT NOT NULL DEFAULT 'pendiente',
                    revisado_por TEXT,
                    revisado_en TIMESTAMPTZ,
                    creado TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    actualizado TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        conn.commit()
    finally:
        conn.close()