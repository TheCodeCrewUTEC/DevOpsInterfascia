from pathlib import Path

from app.services.docling_service import procesar_job

from app.services.chunking_service import (
    generar_chunks
)

from app.services.embedding_service import (
    generar_embeddings
)

from app.services.qwen_service import (
    extraer_campos_formulario
)

from app.services.formulario_job_service import (
    obtener_job,
    actualizar_estado_job
)


async def procesar_formulario(
    ctx,
    job_id: int
):

    print(
        f"[WORKER] Procesando formulario Job {job_id}"
    )

    try:

        # PENDING → PROCESSING
        actualizar_estado_job(
            job_id,
            "PROCESSING"
        )

        # OBTENER JOB
        job = obtener_job(job_id)

        if not job:

            raise Exception(
                f"No existe el Job {job_id}"
            )

        # UBICAR CARPETA
        carpeta_job = (
            Path("storage/formularios")
            / f"job_{job_id}"
        )

        if not carpeta_job.exists():

            raise Exception(
                f"No existe la carpeta del Job: "
                f"{carpeta_job}"
            )

        print(
            f"[WORKER] Carpeta: {carpeta_job}"
        )

        # PROCESAR CON DOCLING
        resultados = procesar_job(
            carpeta_job
        )

        print(
            f"[WORKER] Archivos procesados: "
            f"{len(resultados)}"
        )

        # MOSTRAR RESULTADO DE DOCLING
        for resultado in resultados:

            print(
                f"[DOCLING] Archivo: "
                f"{resultado['nombre']}"
            )

            print(
                f"[DOCLING] Caracteres extraídos: "
                f"{len(resultado['texto'])}"
            )

        # BUSCAR FORMULARIO
        formulario = next(
            (
                resultado
                for resultado in resultados
                if resultado["nombre"]
                == "FormularioPostulacion.pdf"
            ),
            None
        )

        if not formulario:

            raise Exception(
                "No se encontró el formulario "
                "de postulación"
            )

        print(
            f"[WORKER] Formulario encontrado: "
            f"{formulario['nombre']}"
        )

        # QWEN - EXTRAER CAMPOS
        print(
            "[QWEN] Extrayendo campos "
            "del formulario..."
        )

        campos = extraer_campos_formulario(
            formulario["texto"]
        )

        lista_campos = campos.get(
            "campos",
            []
        )

        print(
            f"[QWEN] Campos encontrados: "
            f"{len(lista_campos)}"
        )

        # MOSTRAR CAMPOS EXTRAÍDOS
        for i, campo in enumerate(
            lista_campos,
            start=1
        ):

            print(
                f"\n[CAMPO {i}]"
            )

            print(
                f"Nombre: "
                f"{campo.get('nombre')}"
            )

            print(
                f"Tipo: "
                f"{campo.get('tipo')}"
            )

            print(
                f"Descripción: "
                f"{campo.get('descripcion')}"
            )

        # CHUNKING DE DOCUMENTOS DEL PROYECTO
        for resultado in resultados:

            # No utilizamos el formulario como
            # fuente de información del proyecto
            if resultado["nombre"] == "FormularioPostulacion.pdf":
                continue

            print(
                f"\n[CHUNKING] Generando chunks para: "
                f"{resultado['nombre']}"
            )

            chunks = generar_chunks(
                resultado["documento"]
            )

            print(
                f"[CHUNKING] Chunks generados: "
                f"{len(chunks)}"
            )

            # GENERAR EMBEDDINGS
            embeddings = generar_embeddings(
                chunks
            )

            print(
                f"[EMBEDDING] Resultado obtenido: "
                f"{len(embeddings)} embeddings"
            )

            # MOSTRAR INFORMACIÓN
            for i, item in enumerate(
                embeddings,
                start=1
            ):

                print(
                    f"\n[EMBEDDING {i}]"
                )

                print(
                    f"Texto: "
                    f"{item['texto'][:150]}..."
                )

                print(
                    f"Dimensiones: "
                    f"{len(item['embedding'])}"
                )

        # COMPLETED
        actualizar_estado_job(
            job_id,
            "COMPLETED"
        )

        print(
            f"[WORKER] Job {job_id} "
            f"completado correctamente"
        )

        return {
            "job_id": job_id,
            "estado": "COMPLETED",
            "archivos_procesados": len(resultados),
            "campos_extraidos": len(lista_campos)
        }

    except Exception as e:

        print(
            f"[WORKER] Error procesando Job "
            f"{job_id}: {e}"
        )

        actualizar_estado_job(
            job_id,
            "FAILED"
        )

        raise