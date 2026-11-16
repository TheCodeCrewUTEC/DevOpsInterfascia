import os

from arq import create_pool
from arq.connections import RedisSettings
from arq.jobs import Job

from dotenv import load_dotenv

load_dotenv()

async def encolar_relacionar(conversacion_id: int):
    redis = await create_pool(
        RedisSettings(
            host=os.getenv("REDIS_HOST"),
            port=int(os.getenv("REDIS_PORT")),
            database=int(os.getenv("REDIS_DB"))
        )
    )

    try:
        return await redis.enqueue_job(
            "procesar_relacionar",
            conversacion_id,
            _job_id=f"relacionar_{conversacion_id}",
        )
    finally:
        await redis.close()


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


def _redis():
    return RedisSettings(
        host=os.getenv("REDIS_HOST"),
        port=int(os.getenv("REDIS_PORT")),
        database=int(os.getenv("REDIS_DB"))
    )


async def sacar_formulario_de_la_cola(job_id: int):
    """Saca el job de Redis para que el worker no lo tome ni lo reintente."""

    clave = f"formulario_{job_id}"
    redis = await create_pool(_redis())

    try:
        try:
            await Job(clave, redis).abort()
        except Exception as error:
            print(f"[COLA] No se pudo marcar el abort de {clave}: {error}")

        await redis.zrem("arq:queue", clave)
        await redis.delete(
            f"arq:job:{clave}",
            f"arq:retry:{clave}",
            f"arq:in-progress:{clave}",
            f"arq:result:{clave}",
        )
    finally:
        await redis.close()