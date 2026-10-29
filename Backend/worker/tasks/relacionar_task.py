from app.services.relacionar_chat_service import (
    asegurar_pregunta_inicial,
    carpeta_conversacion,
    guardar_fragmentos,
    marcar_error,
    marcar_lista,
    marcar_procesando,
    obtener_estado,
)


async def procesar_relacionar(ctx, conversacion_id: int):
    estado = obtener_estado(conversacion_id)
    if estado == "READY":
        return
    if ctx.get("job_try", 1) > 1 and estado == "FAILED":
        return

    try:
        marcar_procesando(conversacion_id)
        from app.services.document_embedding_service import (
            generar_chunks_documentos,
            generar_embeddings,
        )

        chunks = generar_chunks_documentos(carpeta_conversacion(conversacion_id))
        if not chunks:
            marcar_error(
                conversacion_id,
                "No pude leer texto en los documentos. Probá con PDF, Word o texto.",
            )
            return

        guardar_fragmentos(conversacion_id, generar_embeddings(chunks))
        asegurar_pregunta_inicial(conversacion_id)
        marcar_lista(conversacion_id)
        print(f"[RELACIONAR] Conversación {conversacion_id} lista ({len(chunks)} fragmentos)")
    except Exception as error:
        print(f"[RELACIONAR] Conversación {conversacion_id}: {error}")
        marcar_error(conversacion_id, "No pude leer los documentos del proyecto.")
