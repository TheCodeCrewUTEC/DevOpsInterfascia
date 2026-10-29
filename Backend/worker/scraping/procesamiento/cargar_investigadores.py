import json
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[4] / ".env")

JSON_FILE = (
    Path(__file__).resolve().parents[1]
    / "spiders"
    / "Investigadores"
    / "Investigadores.json"
)

# Desde la PC el contenedor publica 5433. 5432 es otro Postgres de Windows.
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": int(os.getenv("DB_PORT_PUBLICADO", "5433")),
    "dbname": os.getenv("POSTGRES_DB", "interfascia"),
    "user": os.getenv("POSTGRES_USER", "interfascia"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
}

# El título que se guarda es la formación concluida más alta.
ORDEN_TITULO = (
    "DOCTORADO",
    "MAESTRÍA",
    "ESPECIALIZACIÓN/PERFECCIONAMIENTO",
    "GRADO",
    "PREGRADO",
    "TÉCNICO",
)


def obtener_conexion():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except UnicodeDecodeError:
        raise ConnectionError(
            "Postgres rechazó la conexión y el mensaje vino en español "
            f"(puerto {DB_CONFIG['port']}). "
            "Revisá que Docker publique la base en ese puerto y que "
            "POSTGRES_PASSWORD en .env sea la del usuario interfascia."
        )


def titulo_principal(formacion):
    if not isinstance(formacion, list):
        return None

    concluidas = [
        item for item in formacion
        if isinstance(item, dict) and item.get("estado") == "CONCLUIDA"
    ]
    candidatas = concluidas or [
        item for item in formacion if isinstance(item, dict)
    ]

    for nivel in ORDEN_TITULO:
        for item in candidatas:
            if item.get("nivel") == nivel and item.get("titulo"):
                return item["titulo"].strip()

    for item in candidatas:
        if item.get("titulo"):
            return item["titulo"].strip()
    return None


def investigaciones(proyectos):
    if not isinstance(proyectos, list):
        return None
    lineas = [str(proyecto).strip() for proyecto in proyectos if str(proyecto).strip()]
    return "\n".join(lineas) or None


def cargar():
    if not JSON_FILE.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {JSON_FILE}")

    with JSON_FILE.open(encoding="utf-8") as archivo:
        investigadores = json.load(archivo)

    if not isinstance(investigadores, list):
        raise ValueError("Investigadores.json tiene que ser una lista")

    print(f"Leyendo: {JSON_FILE}")
    print(f"Registros encontrados: {len(investigadores)}")

    conn = obtener_conexion()
    insertados = 0
    actualizados = 0
    omitidos = 0

    try:
        with conn.cursor() as cur:
            for persona in investigadores:
                nombre = str(persona.get("nombre") or "").strip()
                apellido = str(persona.get("apellido") or "").strip()
                if not nombre or not apellido:
                    omitidos += 1
                    continue

                datos = (
                    persona.get("institucion") or None,
                    titulo_principal(persona.get("formacion")),
                    investigaciones(persona.get("proyectos")),
                    persona.get("nivel") or None,
                    persona.get("categoria") or None,
                    persona.get("link") or None,
                    nombre,
                    apellido,
                )

                cur.execute(
                    """
                    UPDATE investigadores
                    SET institucion = %s,
                        titulo = %s,
                        investigaciones = %s,
                        nivel_sni = %s,
                        categoria_sni = %s,
                        fuente = COALESCE(%s, fuente)
                    WHERE lower(nombre) = lower(%s)
                      AND lower(apellido) = lower(%s)
                    """,
                    datos,
                )

                if cur.rowcount:
                    actualizados += cur.rowcount
                    continue

                cur.execute(
                    """
                    INSERT INTO investigadores (
                        institucion,
                        titulo,
                        investigaciones,
                        nivel_sni,
                        categoria_sni,
                        fuente,
                        nombre,
                        apellido
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    datos,
                )
                insertados += 1

        conn.commit()
    finally:
        conn.close()

    print(f"Insertados: {insertados}")
    print(f"Actualizados: {actualizados}")
    print(f"Omitidos: {omitidos}")


if __name__ == "__main__":
    cargar()
