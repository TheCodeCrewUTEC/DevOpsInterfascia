import os

from arq import create_pool
from arq.connections import RedisSettings

from dotenv import load_dotenv

load_dotenv()

async def encolar_formulario(job_id: int):

    redis = await create_pool(
        RedisSettings(
            host=os.getenv("REDIS_HOST"),
            port=int(os.getenv("REDIS_PORT")),
            database=int(os.getenv("REDIS_DB"))
        )
    )

    try:

        job = await redis.enqueue_job(
            "procesar_formulario",
            job_id,
            _job_id=f"formulario_{job_id}"
        )

        return job

    finally:
        await redis.close()