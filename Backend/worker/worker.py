import os
from dotenv import load_dotenv
from arq.connections import RedisSettings
from worker.tasks.formulario_task import procesar_formulario
from worker.tasks.relacionar_task import procesar_relacionar

load_dotenv()

class WorkerSettings:

    functions = [
        procesar_formulario,
        procesar_relacionar,
    ]

    redis_settings = RedisSettings(
        host=os.getenv("REDIS_HOST"),
        port=int(os.getenv("REDIS_PORT")),
        database=int(os.getenv("REDIS_DB"))
    )

    max_jobs = 1