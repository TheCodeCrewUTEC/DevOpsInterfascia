"""Completa convocatoria.fuente e investigadores.fuente desde los JSON del scraping."""

import json
import os
import re
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[4] / ".env")

RAIZ_SPIDERS = Path(__file__).resolve().parents[1] / "spiders"
CONVOCATORIAS_JSON = RAIZ_SPIDERS / "Convocatorias" / "FondosConDocumentos.json"
INVESTIGADORES_JSON = RAIZ_SPIDERS / "Investigadores" / "Investigadores.json"

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": int(os.getenv("DB_PORT_PUBLICADO", "5433")),
    "dbname": os.getenv("POSTGRES_DB", "interfascia"),
    "user": os.getenv("POSTGRES_USER", "interfascia"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
}


def clave(valor: str | None) -> str:
    return re.sub(r"\s+", " ", (valor or "").strip()).casefold()


def enlace(valor) -> str | None:
    if not isinstance(valor, str):
        return None
    limpio = valor.strip()
    if limpio.lower().startswith(("http://", "https://")):
        return limpio
    return None


def mapa_unico(pares: list[tuple[str, str]]) -> dict[str, str]:
    mapa: dict[str, str] = {}
    for clave_item, url in pares:
        if clave_item and url and clave_item not in mapa:
            mapa[clave_item] = url
    return mapa


def cargar() -> None:
    convocatorias = json.loads(CONVOCATORIAS_JSON.read_text(encoding="utf-8"))
    investigadores = json.loads(INVESTIGADORES_JSON.read_text(encoding="utf-8"))

    fuentes_convocatoria = mapa_unico(
        [
            (clave(item.get("nombre")), enlace(item.get("link")))
            for item in convocatorias
            if isinstance(item, dict)
        ]
    )
    fuentes_investigador = mapa_unico(
        [
            (
                f"{clave(item.get('nombre'))}|{clave(item.get('apellido'))}",
                enlace(item.get("link")),
            )
            for item in investigadores
            if isinstance(item, dict)
        ]
    )

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE convocatoria ADD COLUMN IF NOT EXISTS fuente TEXT")
            cur.execute("ALTER TABLE investigadores ADD COLUMN IF NOT EXISTS fuente TEXT")

            cur.execute("SELECT id, titulo FROM convocatoria")
            convocatorias_db = cur.fetchall()
            actualizadas_convocatoria = 0
            for convocatoria_id, titulo in convocatorias_db:
                url = fuentes_convocatoria.get(clave(titulo))
                if not url:
                    continue
                cur.execute(
                    "UPDATE convocatoria SET fuente = %s WHERE id = %s",
                    (url, convocatoria_id),
                )
                actualizadas_convocatoria += 1

            cur.execute("SELECT id, nombre, apellido FROM investigadores")
            investigadores_db = cur.fetchall()
            actualizados_investigador = 0
            for investigador_id, nombre, apellido in investigadores_db:
                url = fuentes_investigador.get(f"{clave(nombre)}|{clave(apellido)}")
                if not url:
                    continue
                cur.execute(
                    "UPDATE investigadores SET fuente = %s WHERE id = %s",
                    (url, investigador_id),
                )
                actualizados_investigador += 1

            cur.execute(
                "SELECT count(*) FROM convocatoria WHERE fuente IS NOT NULL AND btrim(fuente) <> ''"
            )
            con_fuente_convocatoria = cur.fetchone()[0]
            cur.execute(
                "SELECT count(*) FROM investigadores WHERE fuente IS NOT NULL AND btrim(fuente) <> ''"
            )
            con_fuente_investigador = cur.fetchone()[0]

        conn.commit()
    finally:
        conn.close()

    print(f"Convocatorias en JSON con link: {len(fuentes_convocatoria)}")
    print(f"Convocatorias actualizadas: {actualizadas_convocatoria} de {len(convocatorias_db)}")
    print(f"Convocatorias con fuente: {con_fuente_convocatoria}")
    print(f"Investigadores en JSON con link: {len(fuentes_investigador)}")
    print(f"Investigadores actualizados: {actualizados_investigador} de {len(investigadores_db)}")
    print(f"Investigadores con fuente: {con_fuente_investigador}")


if __name__ == "__main__":
    cargar()
