import asyncio

from app.services.deteccion_alertas_service import (
    avisar_cierres,
    enviar_correos_pendientes,
    revisar_convocatorias,
)

# Tareas programadas de alertas (RF005). psycopg2 y smtplib son síncronos,
# por eso corren en un hilo aparte y no frenan el loop de arq.


async def _enviar_correos():
    correos = await asyncio.to_thread(enviar_correos_pendientes)
    print(f"[ALERTAS] Correos: {correos}")
    return correos


async def revisar_alertas(ctx):
    try:
        revision = await asyncio.to_thread(revisar_convocatorias)
        print(f"[ALERTAS] Revisión de convocatorias: {revision}")
        # Los cierres también se recalculan acá (además del cron diario) para no esperar
        # al día siguiente si una convocatoria cambia su fecha; clave_dedup evita repetidos.
        cierres = await asyncio.to_thread(avisar_cierres)
        print(f"[ALERTAS] Avisos de cierre: {cierres}")
        return {"revision": revision, "cierres": cierres, "correos": await _enviar_correos()}
    except Exception as e:
        print(f"[ALERTAS] Error revisando convocatorias: {e}")
        raise


async def avisar_cierres_task(ctx):
    try:
        cierres = await asyncio.to_thread(avisar_cierres)
        print(f"[ALERTAS] Avisos de cierre: {cierres}")
        return {"cierres": cierres, "correos": await _enviar_correos()}
    except Exception as e:
        print(f"[ALERTAS] Error avisando cierres: {e}")
        raise
