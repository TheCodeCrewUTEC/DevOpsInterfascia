import re
import unicodedata

from app.database.connection import get_connection

# Human in the loop: la IA propone, la persona revisa y confirma. Solo lo confirmado
# se guarda acá, por usuario y por campo, para sugerirlo en el próximo formulario.


def clave_campo(campo: str) -> str:
    """'Nombre del proyecto *' y 'NOMBRE DEL PROYECTO:' son el mismo campo."""
    sin_tildes = unicodedata.normalize("NFKD", campo).encode("ascii", "ignore").decode()
    solo_palabras = re.sub(r"[^a-z0-9]+", " ", sin_tildes.lower())
    return solo_palabras.strip()


def confirmar_job(job_id: int, usuario_sub: str) -> int:
    """Guarda las respuestas no vacías del job como datos validados del usuario."""

    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT campo, respuesta, respuesta_ia, editada
                    FROM respuesta_formulario
                    WHERE job_id = %s
                      AND btrim(COALESCE(respuesta, '')) <> ''
                    ORDER BY id
                    """,
                    (job_id,)
                )

                guardados = 0

                for campo, respuesta, respuesta_ia, editada in cur.fetchall():
                    clave = clave_campo(campo)
                    if not clave:
                        continue

                    cur.execute(
                        """
                        INSERT INTO dato_proyecto_validado (
                            usuario_sub, campo_clave, campo, valor,
                            respuesta_ia, editado_por_usuario, job_id
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (usuario_sub, campo_clave) DO UPDATE SET
                            campo = EXCLUDED.campo,
                            valor = EXCLUDED.valor,
                            respuesta_ia = EXCLUDED.respuesta_ia,
                            editado_por_usuario = EXCLUDED.editado_por_usuario,
                            job_id = EXCLUDED.job_id,
                            veces_confirmado = dato_proyecto_validado.veces_confirmado + 1,
                            actualizado = NOW()
                        """,
                        (
                            usuario_sub,
                            clave,
                            campo,
                            respuesta.strip(),
                            respuesta_ia,
                            bool(editada),
                            job_id,
                        )
                    )
                    guardados += 1

                cur.execute(
                    "UPDATE formulario_job SET validado_en = NOW() WHERE id = %s",
                    (job_id,)
                )

                return guardados

    finally:
        conn.close()


def datos_del_usuario(cur, usuario_sub: str) -> dict[str, str]:
    """campo_clave → valor confirmado, para sugerir en un formulario nuevo."""

    cur.execute(
        """
        SELECT campo_clave, valor
        FROM dato_proyecto_validado
        WHERE usuario_sub = %s
        """,
        (usuario_sub,)
    )

    return dict(cur.fetchall())
