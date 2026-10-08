from pathlib import Path

from app.services.docling_service import procesar_job
from app.services.respuesta_service_db import guardar_respuesta
from app.services.qwen_service import (
    extraer_campos_formulario
)

from app.services.formulario_job_service import (
    obtener_job,
    actualizar_estado_job
)

from app.services.document_embedding_service import (
    generar_chunks_documentos,
    generar_embeddings,
    buscar_chunks_relevantes,
)

from app.services.respuesta_service import (
    cabe_documento_completo,
    generar_respuesta,
)


def fuente_desde_chunk(chunk: dict):
    archivo = chunk.get("documento")

    if not archivo:
        return None

    return {
        "pagina": chunk.get("pagina"),
        "archivo": archivo,
    }


async def procesar_formulario(
    ctx,
    job_id: int
):

    print(
        f"[WORKER] Procesando formulario Job {job_id}"
    )

    try:

        # ==========================================
        # 1. PENDING → PROCESSING
        # ==========================================

        actualizar_estado_job(
            job_id,
            "PROCESSING"
        )

        # ==========================================
        # 2. OBTENER JOB
        # ==========================================

        job = obtener_job(job_id)

        if not job:
            raise Exception(
                f"No existe el Job {job_id}"
            )

        formulario_path = job[2]

        if not formulario_path:
            raise Exception(
                f"El Job {job_id} no tiene "
                "la ruta del formulario"
            )

        nombre_formulario = Path(formulario_path).name

        print(
            f"[WORKER] Formulario esperado: "
            f"{nombre_formulario}"
        )

        # ==========================================
        # 3. UBICAR CARPETA
        # ==========================================

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

        # ==========================================
        # 4. PROCESAR CON DOCLING
        # ==========================================

        resultados = procesar_job(
            carpeta_job
        )

        print(
            f"[WORKER] Archivos procesados: "
            f"{len(resultados)}"
        )

        # ==========================================
        # 5. MOSTRAR RESULTADO DE DOCLING
        # ==========================================

        for resultado in resultados:

            print(
                f"[DOCLING] Archivo: "
                f"{resultado['nombre']}"
            )

            print(
                f"[DOCLING] Caracteres extraídos: "
                f"{len(resultado['texto'])}"
            )

        # ==========================================
        # 6. BUSCAR FORMULARIO
        # ==========================================

        formulario = next(
            (
                resultado
                for resultado in resultados
                if resultado["nombre"]
                == nombre_formulario
            ),
            None
        )

        if not formulario:
            nombres = ", ".join(
                resultado["nombre"]
                for resultado in resultados
            )
            raise Exception(
                "No se encontró el formulario "
                f"de postulación: {nombre_formulario}. "
                f"Archivos: {nombres}"
            )

        print(
            f"[WORKER] Formulario encontrado: "
            f"{formulario['nombre']}"
        )

        # ==========================================
        # 7. MOSTRAR INFORMACIÓN DEL FORMULARIO
        # ==========================================

        print(
            f"[QWEN] Texto del formulario: "
            f"{len(formulario['texto'])} caracteres"
        )

        # ==========================================
        # 8. OBTENER RUTA REAL DEL PDF
        # ==========================================

        ruta_formulario = (
            carpeta_job
            / formulario["nombre"]
        )

        if not ruta_formulario.exists():
            raise Exception(
                f"No existe el archivo del formulario: "
                f"{ruta_formulario}"
            )

        print(
            f"[QWEN] Archivo utilizado: "
            f"{ruta_formulario}"
        )

        # ==========================================
        # 9. EXTRAER CAMPOS CON QWEN
        # ==========================================

        print(
            "[QWEN] Extrayendo campos "
            "del formulario..."
        )

        campos = extraer_campos_formulario(
            ruta_formulario,
            formulario["documento"]
        )

        # ==========================================
        # 10. VALIDAR RESULTADO
        # ==========================================

        if not isinstance(
            campos,
            dict
        ):
            raise Exception(
                "La extracción no devolvió "
                "un objeto válido"
            )

        lista_campos = campos.get(
            "campos",
            []
        )

        if not isinstance(
            lista_campos,
            list
        ):
            raise Exception(
                "La lista de campos no es válida"
            )

        print(
            f"\n[QWEN] Campos encontrados: "
            f"{len(lista_campos)}"
        )

        # ============================================================
        # PROCESAR DOCUMENTOS DEL USUARIO
        # ============================================================

        print()
        print("=" * 60)
        print("[WORKER] Procesando documentos del usuario")
        print("=" * 60)

        # Reutiliza las conversiones de Docling del paso 4
        chunks = generar_chunks_documentos(
            carpeta_job,
            {r["nombre"]: r["documento"] for r in resultados}
        )

        print(
            f"[WORKER] Chunks generados: {len(chunks)}"
        )

        chunks = generar_embeddings(chunks)

        print(
            f"[WORKER] Embeddings generados: {len(chunks)}"
        )

        # ============================================================
        # BUSCAR INFORMACIÓN PARA CADA CAMPO
        # ============================================================

        print()
        print("=" * 60)
        print("[WORKER] BUSCANDO INFORMACIÓN PARA CADA CAMPO")
        print("=" * 60)

        respuestas = []

        usar_documento_completo = cabe_documento_completo(chunks)

        print(
            "[WORKER] Contexto por campo: "
            + (
                "documento completo (caché de Ollama)"
                if usar_documento_completo
                else "5 chunks más relevantes"
            )
        )

        for campo in lista_campos:

            nombre_campo = campo.get("campo")
            tipo_campo = campo.get("tipo")

            print("\n" + "=" * 70)
            print(f"[WORKER] PROCESANDO CAMPO: {nombre_campo}")
            print(f"[WORKER] Tipo: {tipo_campo}")
            print("=" * 70)

            # ============================================================
            # 1. BÚSQUEDA SEMÁNTICA
            # ============================================================

            # Documento chico: siempre los mismos chunks y en el mismo orden
            resultados = (
                chunks
                if usar_documento_completo
                else buscar_chunks_relevantes(
                    nombre_campo,
                    chunks,
                    top_k=5,
                )
            )

            print(f"[WORKER] Chunks encontrados: {len(resultados)}")

            # ============================================================
            # 2. GENERAR RESPUESTA CON QWEN
            # ============================================================

            resultado_qwen = generar_respuesta(
                campo=nombre_campo,
                tipo=tipo_campo,
                chunks_relevantes=resultados,
            )

            respuesta = resultado_qwen.get("respuesta")

            # ============================================================
            # 3. NORMALIZAR "null"
            # ============================================================

            if respuesta == "null":
                respuesta = None

            # ============================================================
            # 4. TRANSFORMAR FUENTES
            # ============================================================

            fuentes_qwen = resultado_qwen.get("fuentes", [])

            fuentes = []

            for fuente in fuentes_qwen:

                chunk_id = None

                if isinstance(fuente, dict):
                    chunk_id = fuente.get("chunk", fuente.get("chunk_id"))
                elif isinstance(fuente, int):
                    chunk_id = fuente

                if isinstance(chunk_id, str) and chunk_id.isdigit():
                    chunk_id = int(chunk_id)

                if not isinstance(chunk_id, int):
                    continue

                # Los chunks recuperados están numerados desde 1
                # según el orden enviado a Qwen.
                indice = chunk_id - 1

                if indice < 0 or indice >= len(resultados):
                    continue

                fuente_documento = fuente_desde_chunk(resultados[indice])

                if fuente_documento is not None:
                    fuentes.append(fuente_documento)

            if not fuentes and respuesta:
                texto_respuesta = str(respuesta).strip().lower()

                for chunk in resultados:
                    texto_chunk = str(chunk.get("texto", "")).lower()

                    if texto_respuesta and texto_respuesta in texto_chunk:
                        fuente_documento = fuente_desde_chunk(chunk)

                        if fuente_documento is not None:
                            fuentes.append(fuente_documento)

            # ============================================================
            # 5. ELIMINAR FUENTES DUPLICADAS
            # ============================================================

            fuentes_unicas = []

            for fuente in fuentes:

                if fuente not in fuentes_unicas:
                    fuentes_unicas.append(fuente)

            # ============================================================
            # 6. GUARDAR EN BASE DE DATOS
            # ============================================================

            pagina = campo.get("pagina")

            guardar_respuesta(
                job_id=job_id,
                campo=nombre_campo,
                respuesta=respuesta,
                fuentes=fuentes_unicas,
                tipo=tipo_campo,
                pagina=pagina if isinstance(pagina, int) else None,
            )

            # ============================================================
            # 7. RESULTADO DEL CAMPO
            # ============================================================

            resultado_campo = {
                "campo": nombre_campo,
                "respuesta": respuesta,
                "fuentes": fuentes_unicas,
            }

            respuestas.append(resultado_campo)

            print(f"[WORKER] RESPUESTA FINAL: {respuesta}")
            print(f"[WORKER] FUENTES: {fuentes_unicas}")

        # ==========================================
        # 12. COMPLETED
        # ==========================================

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