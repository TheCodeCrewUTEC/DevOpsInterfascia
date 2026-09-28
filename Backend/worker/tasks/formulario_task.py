async def procesar_formulario(ctx, job_id: int):

    print(
        f"[WORKER] Procesando formulario Job {job_id}"
    )

    return {
        "job_id": job_id,
        "mensaje": "Job recibido correctamente"
    }