from app.database.connection import get_connection

# Alertas y notificaciones (RF005). Cada fila de convocatoria es un fondo; el usuario
# se suscribe a una convocatoria puntual, a una institución o a una temática.
# Todas las consultas filtran por usuario_sub: nadie ve ni toca lo de otro.

# Misma lista que `tematicas` en Frontend/app/repositorio/page.tsx
TEMATICAS = (
    "Innovación",
    "Tecnología",
    "Agricultura",
    "Salud",
    "Educación",
    "Energía",
    "Medio ambiente",
)
TIPOS_ALERTA = ("apertura", "cierre", "actualizacion")

PREFERENCIAS_POR_DEFECTO = {
    "alerta_apertura": True,
    "alerta_cierre": True,
    "alerta_actualizacion": True,
    "dias_anticipacion_cierre": 7,
    "email_habilitado": False,
    "email_habilitado_desde": None,
    "email": None,
}

COLUMNAS_SUSCRIPCION = """
    s.id, s.tipo, s.convocatoria_id, s.valor, c.titulo AS titulo_convocatoria, s.creado
"""
COLUMNAS_PREFERENCIAS = """
    alerta_apertura, alerta_cierre, alerta_actualizacion, dias_anticipacion_cierre,
    email_habilitado, email_habilitado_desde, email
"""
COLUMNAS_NOTIFICACION = """
    id, tipo, convocatoria_id, titulo, mensaje, detalle, leida, creado, email_enviado_en
"""


def _fila(cur, row) -> dict | None:
    if row is None:
        return None
    return {col[0]: valor for col, valor in zip(cur.description, row)}


def _filas(cur) -> list[dict]:
    return [_fila(cur, row) for row in cur.fetchall()]


# --- Suscripciones ---

def listar_suscripciones(usuario_sub: str) -> list[dict]:
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {COLUMNAS_SUSCRIPCION}
                FROM suscripcion s
                LEFT JOIN convocatoria c ON c.id = s.convocatoria_id
                WHERE s.usuario_sub = %s
                ORDER BY s.creado DESC, s.id DESC
                """,
                (usuario_sub,)
            )
            return _filas(cur)
    finally:
        conn.close()


def crear_suscripcion(
    usuario_sub: str,
    tipo: str,
    convocatoria_id: int | None,
    valor: str | None,
) -> tuple[dict, bool]:
    """Devuelve (suscripción, creada). Si ya existía, devuelve la existente y False."""

    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO suscripcion (usuario_sub, tipo, convocatoria_id, valor)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    RETURNING id
                    """,
                    (usuario_sub, tipo, convocatoria_id, valor)
                )
                insertada = cur.fetchone()

                if insertada is not None:
                    condicion = "s.id = %s"
                    parametros = (insertada[0], usuario_sub)
                else:
                    # Misma expresión que el índice único suscripcion_unica
                    condicion = """
                        s.tipo = %s
                        AND COALESCE(s.convocatoria_id, 0) = COALESCE(%s, 0)
                        AND COALESCE(lower(s.valor), '') = COALESCE(lower(%s), '')
                    """
                    parametros = (tipo, convocatoria_id, valor, usuario_sub)

                cur.execute(
                    f"""
                    SELECT {COLUMNAS_SUSCRIPCION}
                    FROM suscripcion s
                    LEFT JOIN convocatoria c ON c.id = s.convocatoria_id
                    WHERE {condicion}
                      AND s.usuario_sub = %s
                    """,
                    parametros
                )
                return _fila(cur, cur.fetchone()), insertada is not None
    finally:
        conn.close()


def existe_convocatoria(id: int) -> bool:
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM convocatoria WHERE id = %s", (id,))
            return cur.fetchone() is not None
    finally:
        conn.close()


def eliminar_suscripcion(usuario_sub: str, id: int) -> bool:
    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM suscripcion WHERE id = %s AND usuario_sub = %s",
                    (id, usuario_sub)
                )
                return cur.rowcount > 0
    finally:
        conn.close()


# --- Preferencias ---

def obtener_preferencias(usuario_sub: str) -> dict:
    """Si el usuario nunca las guardó, devuelve los valores por defecto (sin insertar)."""

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {COLUMNAS_PREFERENCIAS}
                FROM preferencia_notificacion
                WHERE usuario_sub = %s
                """,
                (usuario_sub,)
            )
            return _fila(cur, cur.fetchone()) or dict(PREFERENCIAS_POR_DEFECTO)
    finally:
        conn.close()


def guardar_preferencias(usuario_sub: str, datos: dict, email: str | None) -> dict:
    """UPSERT. email_habilitado_desde marca desde cuándo se mandan correos: se fija al
    habilitarlo, se mantiene mientras siga habilitado y se borra al deshabilitarlo."""

    email = (email or "").strip() or None
    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO preferencia_notificacion (
                        usuario_sub, alerta_apertura, alerta_cierre, alerta_actualizacion,
                        dias_anticipacion_cierre, email_habilitado, email_habilitado_desde, email
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, CASE WHEN %s THEN NOW() END, %s)
                    ON CONFLICT (usuario_sub) DO UPDATE SET
                        alerta_apertura = EXCLUDED.alerta_apertura,
                        alerta_cierre = EXCLUDED.alerta_cierre,
                        alerta_actualizacion = EXCLUDED.alerta_actualizacion,
                        dias_anticipacion_cierre = EXCLUDED.dias_anticipacion_cierre,
                        email_habilitado = EXCLUDED.email_habilitado,
                        email_habilitado_desde = CASE
                            WHEN NOT EXCLUDED.email_habilitado THEN NULL
                            WHEN preferencia_notificacion.email_habilitado
                                THEN COALESCE(preferencia_notificacion.email_habilitado_desde, NOW())
                            ELSE NOW()
                        END,
                        email = COALESCE(EXCLUDED.email, preferencia_notificacion.email),
                        actualizado = NOW()
                    RETURNING {COLUMNAS_PREFERENCIAS}
                    """,
                    (
                        usuario_sub,
                        bool(datos["alerta_apertura"]),
                        bool(datos["alerta_cierre"]),
                        bool(datos["alerta_actualizacion"]),
                        int(datos["dias_anticipacion_cierre"]),
                        bool(datos["email_habilitado"]),
                        bool(datos["email_habilitado"]),
                        email,
                    )
                )
                return _fila(cur, cur.fetchone())
    finally:
        conn.close()


# --- Notificaciones ---

def listar_notificaciones(
    usuario_sub: str,
    solo_no_leidas: bool = False,
    tipo: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> dict:
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            where = " AND NOT leida" if solo_no_leidas else ""
            parametros = [usuario_sub]

            if tipo:
                where += " AND tipo = %s"
                parametros.append(tipo)

            cur.execute(
                f"""
                SELECT COUNT(*)
                FROM notificacion
                WHERE usuario_sub = %s AND NOT eliminada
                {where}
                """,
                parametros
            )
            total = cur.fetchone()[0]

            cur.execute(
                f"""
                SELECT {COLUMNAS_NOTIFICACION}
                FROM notificacion
                WHERE usuario_sub = %s AND NOT eliminada
                {where}
                ORDER BY creado DESC, id DESC
                LIMIT %s
                OFFSET %s
                """,
                parametros + [limit, (page - 1) * limit]
            )
            items = _filas(cur)

            # Para el contador de la campana: no depende de los filtros
            cur.execute(
                """
                SELECT COUNT(*)
                FROM notificacion
                WHERE usuario_sub = %s AND NOT eliminada AND NOT leida
                """,
                (usuario_sub,)
            )
            no_leidas = cur.fetchone()[0]
    finally:
        conn.close()

    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": (total + limit - 1) // limit,
        "no_leidas": no_leidas,
    }


def obtener_notificacion(usuario_sub: str, id: int) -> dict | None:
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {COLUMNAS_NOTIFICACION}
                FROM notificacion
                WHERE id = %s AND usuario_sub = %s AND NOT eliminada
                """,
                (id, usuario_sub)
            )
            return _fila(cur, cur.fetchone())
    finally:
        conn.close()


def marcar_leida(usuario_sub: str, id: int, leida: bool) -> dict | None:
    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE notificacion
                    SET leida = %s
                    WHERE id = %s AND usuario_sub = %s AND NOT eliminada
                    RETURNING {COLUMNAS_NOTIFICACION}
                    """,
                    (leida, id, usuario_sub)
                )
                return _fila(cur, cur.fetchone())
    finally:
        conn.close()


def marcar_todas_leidas(usuario_sub: str) -> int:
    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE notificacion
                    SET leida = TRUE
                    WHERE usuario_sub = %s AND NOT eliminada AND NOT leida
                    """,
                    (usuario_sub,)
                )
                return cur.rowcount
    finally:
        conn.close()


def eliminar_notificacion(usuario_sub: str, id: int) -> bool:
    """Borrado lógico: la fila queda para que clave_dedup no la vuelva a generar."""

    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE notificacion
                    SET eliminada = TRUE
                    WHERE id = %s AND usuario_sub = %s AND NOT eliminada
                    """,
                    (id, usuario_sub)
                )
                return cur.rowcount > 0
    finally:
        conn.close()


def eliminar_leidas(usuario_sub: str) -> int:
    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE notificacion
                    SET eliminada = TRUE
                    WHERE usuario_sub = %s AND leida AND NOT eliminada
                    """,
                    (usuario_sub,)
                )
                return cur.rowcount
    finally:
        conn.close()


# --- Opciones para los formularios ---

def instituciones_disponibles() -> list[str]:
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT btrim(institucion)
                FROM convocatoria
                WHERE btrim(COALESCE(institucion, '')) <> ''
                ORDER BY 1
                """
            )
            return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()
