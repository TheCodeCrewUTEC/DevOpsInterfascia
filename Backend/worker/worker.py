import os
from dotenv import load_dotenv
from arq.connections import RedisSettings
from worker.tasks.formulario_task import procesar_formulario

load_dotenv()

class WorkerSettings:

    functions = [
        procesar_formulario
    ]

    redis_settings = RedisSettings(
        host=os.getenv("REDIS_HOST"),
        port=int(os.getenv("REDIS_PORT")),
        database=int(os.getenv("REDIS_DB"))
    )

    max_jobs = 1