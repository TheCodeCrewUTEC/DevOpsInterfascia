import importlib.util
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from scrapy.crawler import CrawlerProcess

load_dotenv(Path(__file__).resolve().parents[4] / ".env")

# Desde la PC el contenedor publica 5433. 5432 es otro Postgres de Windows.
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": int(os.getenv("DB_PORT_PUBLICADO", "5433")),
    "dbname": os.getenv("POSTGRES_DB", "interfascia"),
    "user": os.getenv("POSTGRES_USER", "interfascia"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
}

SPIDER = (
    Path(__file__).resolve().parents[1]
    / "spiders"
    / "Proyectos"
    / "aniispider.py"
)


def _texto(item, *claves):
    for clave in claves:
        valor = str(item.get(clave) or "").strip()
        if valor:
            return valor
    return None


def preparar_tabla(conn):
    with conn.cursor() as cur:
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
    conn.commit()


class GuardarProyectosPipeline:
    def open_spider(self, spider):
        self.conn = psycopg2.connect(**DB_CONFIG)
        preparar_tabla(self.conn)
        self.guardados = 0
        self.omitidos = 0

    def close_spider(self, spider):
        self.conn.commit()
        self.conn.close()
        print(f"Guardados: {self.guardados}")
        print(f"Omitidos: {self.omitidos}")

    def process_item(self, item, spider):
        fuente = _texto(item, "link")
        nombre = _texto(item, "titulo")
        if not fuente or not nombre:
            self.omitidos += 1
            return item

        descripcion = _texto(item, "resumen_final", "resumen_inicial", "resumen")
        beneficiario = _texto(item, "beneficiario")
        datos = (
            nombre,
            _texto(item, "estado"),
            _texto(item, "anio_convocatoria"),
            descripcion,
            beneficiario,
            _texto(item, "codigo"),
            fuente,
            beneficiario,
            _texto(item, "instrumento"),
            _texto(item, "sector"),
            _texto(item, "area_proyecto", "area"),
            _texto(item, "subsidio"),
            _texto(item, "fecha_inicio"),
            _texto(item, "duracion"),
            _texto(item, "fase"),
        )
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO proyectos (
                    nombre, estado, anio, descripcion, investigadores,
                    codigo, fuente, beneficiario, instrumento, sector, area,
                    subsidio, fecha_inicio, duracion, fase
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fuente) DO UPDATE SET
                    nombre = EXCLUDED.nombre,
                    estado = EXCLUDED.estado,
                    anio = EXCLUDED.anio,
                    descripcion = EXCLUDED.descripcion,
                    investigadores = EXCLUDED.investigadores,
                    codigo = EXCLUDED.codigo,
                    beneficiario = EXCLUDED.beneficiario,
                    instrumento = EXCLUDED.instrumento,
                    sector = EXCLUDED.sector,
                    area = EXCLUDED.area,
                    subsidio = EXCLUDED.subsidio,
                    fecha_inicio = EXCLUDED.fecha_inicio,
                    duracion = EXCLUDED.duracion,
                    fase = EXCLUDED.fase
                """,
                datos,
            )
        self.guardados += 1
        if self.guardados % 25 == 0:
            self.conn.commit()
            print(f"Guardados: {self.guardados}", flush=True)
        return item


def _spider():
    spec = importlib.util.spec_from_file_location("aniispider", SPIDER)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.AniiSpyder


def cargar(limit=0):
    if not SPIDER.is_file():
        raise FileNotFoundError(f"No se encontró el spider: {SPIDER}")

    proceso = CrawlerProcess(
        settings={
            "ITEM_PIPELINES": {
                "worker.scraping.procesamiento.cargar_proyectos.GuardarProyectosPipeline": 100,
            },
            "LOG_LEVEL": "INFO",
            "ROBOTSTXT_OBEY": False,
        }
    )
    proceso.crawl(_spider(), limit=limit)
    proceso.start()


if __name__ == "__main__":
    import sys

    tope = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    cargar(tope)
