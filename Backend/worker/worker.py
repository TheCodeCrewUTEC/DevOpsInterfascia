import asyncio
import os
from dotenv import load_dotenv
from arq import cron
from arq.connections import RedisSettings
from app.database.connection import ensure_schema
from worker.tasks.formulario_task import procesar_formulario
from worker.tasks.alertas_task import avisar_cierres_task, revisar_alertas
from worker.tasks.relacionar_task import procesar_relacionar

load_dotenv()


async def preparar_esquema(ctx):
    # En un deploy limpio el worker puede arrancar antes que el backend: sin esto el
    # cron de alertas falla porque las tablas todavía no existen.
    try:
        await asyncio.to_thread(ensure_schema)
    except Exception as e:
        print(f"[WORKER] No se pudo preparar el esquema de la base: {e}")


class WorkerSettings:

    on_startup = preparar_esquema

    functions = [
        procesar_formulario,
        revisar_alertas,
        avisar_cierres_task,
        procesar_relacionar
    ]

    # Alertas (RF005): revisión de convocatorias cada media hora y avisos de cierre
    # una vez por día. El contenedor está en UTC: 11:00 UTC son las 8:00 en Uruguay.
    cron_jobs = [
        cron(revisar_alertas, minute={0, 30}),
        cron(avisar_cierres_task, hour={11}, minute={0})
    ]

    redis_settings = RedisSettings(
        host=os.getenv("REDIS_HOST"),
        port=int(os.getenv("REDIS_PORT")),
        database=int(os.getenv("REDIS_DB"))
    )

    max_jobs = 1
