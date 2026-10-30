import os
import time

import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Clave de pg_advisory_xact_lock para ensure_schema (5005 y 5006 son de las alertas)
BLOQUEO_ESQUEMA = 5004

SEGUNDOS_CONEXION_POR_DEFECTO = 5


def segundos_conexion() -> int:
    """Lee DB_CONNECT_TIMEOUT sin lanzar nunca.

    Vacío o no numérico ("5s") → 5. Menor que 1 → 1, porque con 0 libpq espera sin límite.
    """

    try:
        segundos = int((os.getenv("DB_CONNECT_TIMEOUT") or "").strip())
    except ValueError:
        return SEGUNDOS_CONEXION_POR_DEFECTO
    return max(segundos, 1)


def get_connection():
    port = os.getenv("DB_PORT")
    # Sin límite, con la base caída cada conexión espera lo que decida el sistema operativo.
    # Solo afecta al conectar, no a la duración de las consultas.
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=int(port) if port else None,
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=segundos_conexion()
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
            # Backend y worker corren esto al arrancar: sin el lock, en una base vacía los
            # CREATE TABLE IF NOT EXISTS simultáneos chocan en el catálogo (UniqueViolation).
            # Todo va en una sola transacción, así que el lock se libera con el commit.
            cur.execute("SELECT pg_advisory_xact_lock(%s)", (BLOQUEO_ESQUEMA,))
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
            cur.execute(
                """
                ALTER TABLE convocatoria
                    ADD COLUMN IF NOT EXISTS fuente TEXT
                """
            )
            cur.execute(
                """
                ALTER TABLE investigadores
                    ADD COLUMN IF NOT EXISTS fuente TEXT
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS relacionar_conversacion (
                    id SERIAL PRIMARY KEY,
                    usuario_sub TEXT NOT NULL,
                    estado TEXT NOT NULL,
                    error TEXT,
                    documentos TEXT[] NOT NULL DEFAULT '{}',
                    creado TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    listo TIMESTAMPTZ
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS relacionar_mensaje (
                    id SERIAL PRIMARY KEY,
                    conversacion_id INTEGER NOT NULL
                        REFERENCES relacionar_conversacion(id) ON DELETE CASCADE,
                    rol TEXT NOT NULL,
                    contenido TEXT NOT NULL,
                    fondos JSONB,
                    creado TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                """
                ALTER TABLE relacionar_mensaje
                    ADD COLUMN IF NOT EXISTS fondos JSONB
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
            cur.execute("ALTER TABLE proyectos ADD COLUMN IF NOT EXISTS codigo TEXT")
            cur.execute("ALTER TABLE proyectos ADD COLUMN IF NOT EXISTS fuente TEXT")
            cur.execute("ALTER TABLE proyectos ADD COLUMN IF NOT EXISTS beneficiario TEXT")
            cur.execute("ALTER TABLE proyectos ADD COLUMN IF NOT EXISTS instrumento TEXT")
            cur.execute("ALTER TABLE proyectos ADD COLUMN IF NOT EXISTS sector TEXT")
            cur.execute("ALTER TABLE proyectos ADD COLUMN IF NOT EXISTS area TEXT")
            cur.execute("ALTER TABLE proyectos ADD COLUMN IF NOT EXISTS subsidio TEXT")
            cur.execute("ALTER TABLE proyectos ADD COLUMN IF NOT EXISTS fecha_inicio TEXT")
            cur.execute("ALTER TABLE proyectos ADD COLUMN IF NOT EXISTS duracion TEXT")
            cur.execute("ALTER TABLE proyectos ADD COLUMN IF NOT EXISTS fase TEXT")
            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS proyectos_fuente_unica
                ON proyectos (fuente)
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
            # Alertas (RF005). Cada fila de convocatoria es un fondo; esa tabla viene de una
            # base existente y no se crea acá, por eso convocatoria_id no tiene FK.
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
                    ON suscripcion (usuario_sub, tipo, COALESCE(convocatoria_id, 0), COALESCE(lower(valor), ''))
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS suscripcion_por_usuario ON suscripcion (usuario_sub)"
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
            # clave_dedup evita repetir la misma alerta al mismo usuario
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
                CREATE INDEX IF NOT EXISTS notificacion_por_usuario
                    ON notificacion (usuario_sub, eliminada, creado DESC)
                """
            )
            # Última foto de cada convocatoria, para detectar cambios entre corridas
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
            # Métricas de uso (RF006-08): la llena el middleware de app/main.py.
            # Solo funcionalidad, usuario y fecha; nunca términos de búsqueda.
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS evento_uso (
                    id BIGSERIAL PRIMARY KEY,
                    tipo TEXT NOT NULL,
                    usuario_sub TEXT,
                    creado TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS evento_uso_creado ON evento_uso (creado)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS evento_uso_tipo_creado ON evento_uso (tipo, creado)"
            )
        conn.commit()
    finally:
        conn.close()