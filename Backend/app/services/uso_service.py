import os
import re
import threading
import time as reloj
from collections.abc import Mapping
from datetime import date, datetime, time, timedelta

import jwt
import psycopg2
from starlette.background import BackgroundTask, BackgroundTasks

from app.database.connection import get_connection
from app.services.deteccion_alertas_service import ZONA_URUGUAY

# Métricas de uso de la plataforma (RF006-08). Un middleware HTTP clasifica cada
# request por funcionalidad y guarda una fila en evento_uso. Prometheus no sirve para
# esto: no sabe qué usuario hizo la request.
# Privacidad: solo se guarda el tipo de funcionalidad, el usuario y la fecha. Nunca los
# términos de búsqueda ni otros parámetros.

FUNCIONALIDADES = {
    "busqueda_repositorio": "Búsquedas en el repositorio",
    "consulta_repositorio": "Consultas al repositorio",
    "detalle_fondo": "Detalle de fondos",
    "consultor_formulario": "Formularios enviados al Consultor IA",
    "consultor_confirmacion": "Formularios confirmados",
    "analisis_datos": "Análisis de datos",
    "alerta_suscripcion": "Suscripciones a alertas",
    "alertas_consulta": "Consultas de alertas",
    "perfil_actualizacion": "Actualizaciones de perfil",
}

ESTADOS_USUARIO = {
    "pendiente": "Pendiente",
    "aprobado": "Aprobado",
    "rechazado": "Rechazado",
}

SIN_DATO = "Sin dato"

# Un sub de Keycloak es un UUID; el límite evita que un token armado a mano llene la tabla
LARGO_MAXIMO_SUB = 255

# Rutas exactas (sin barra final) → funcionalidad. Verificadas contra los routers:
# convocatorias.py (prefijo /api/convocatorias, la lista está en "/"), formularios.py
# (prefijo /formularios, sin /api), analisis.py, alertas.py y perfil.py.
# /api/proyectos y /api/investigadores no se cuentan: el repositorio los consulta junto
# con convocatorias en cada búsqueda y se contaría triple.
RUTAS_FIJAS = {
    ("POST", "/formularios/jobs"): "consultor_formulario",
    ("POST", "/api/alertas/suscripciones"): "alerta_suscripcion",
    ("GET", "/api/alertas/notificaciones"): "alertas_consulta",
    ("PUT", "/api/perfil"): "perfil_actualizacion",
}

PATRON_DETALLE_FONDO = re.compile(r"^/api/convocatorias/\d+$")
PATRON_CONFIRMACION = re.compile(r"^/formularios/jobs/\d+/confirmar$")
PATRON_ANALISIS = re.compile(r"^/api/analisis/(resumen|fondos|investigadores|proyectos|tendencias)$")


def clasificar(metodo: str, ruta: str, query: Mapping[str, str], status: int) -> str | None:
    """Devuelve la clave de FUNCIONALIDADES que corresponde a la request, o None si no se cuenta."""

    # Solo respuestas exitosas. Los 3xx tampoco: /api/convocatorias sin barra responde
    # 307 hacia /api/convocatorias/ y se contaría dos veces.
    if status < 200 or status >= 300:
        return None

    metodo = (metodo or "").upper()
    ruta = (ruta or "").rstrip("/") or "/"

    if metodo == "GET" and ruta == "/api/convocatorias":
        buscar = (query.get("buscar") or "").strip()
        return "busqueda_repositorio" if buscar else "consulta_repositorio"

    if metodo == "GET" and PATRON_DETALLE_FONDO.match(ruta):
        return "detalle_fondo"

    if metodo == "POST" and PATRON_CONFIRMACION.match(ruta):
        return "consultor_confirmacion"

    if metodo == "GET" and PATRON_ANALISIS.match(ruta):
        return "analisis_datos"

    return RUTAS_FIJAS.get((metodo, ruta))


def sub_sin_verificar(authorization: str | None) -> str | None:
    """Lee el claim "sub" del Bearer SIN verificar la firma.

    Es solo para la estadística de usuarios distintos: el token se valida (o no) en las
    dependencias de cada ruta. Este valor nunca se usa para autorizar nada.
    Por eso "usuarios distintos" es aproximado: en las rutas públicas (repositorio,
    detalle de fondo) cualquiera puede mandar un token inventado con otro sub.
    """

    try:
        tipo, _, token = (authorization or "").strip().partition(" ")
        if tipo.lower() != "bearer" or not token.strip():
            return None

        claims = jwt.decode(token.strip(), options={"verify_signature": False})
        sub = claims.get("sub")
        if not isinstance(sub, str) or not sub.strip():
            return None
        return sub.strip()[:LARGO_MAXIMO_SUB]
    except Exception:
        return None


# Corte ante la base caída: cada intento de conexión ocupa un hilo del threadpool hasta
# DB_CONNECT_TIMEOUT. Si un registro falla al conectar, los siguientes se descartan sin
# intentar durante SEGUNDOS_PAUSA (esos eventos se pierden; es solo estadística).
SEGUNDOS_PAUSA = 30
_bloqueo_pausa = threading.Lock()
_pausado_hasta = 0.0


def en_pausa() -> bool:
    with _bloqueo_pausa:
        return reloj.monotonic() < _pausado_hasta


def _pausar(error) -> None:
    global _pausado_hasta
    with _bloqueo_pausa:
        ahora = reloj.monotonic()
        ya_pausado = ahora < _pausado_hasta
        _pausado_hasta = ahora + SEGUNDOS_PAUSA
    # Una sola línea por corte, aunque fallen varios registros a la vez
    if not ya_pausado:
        print(f"[USO] Sin conexión a la base; no se registra el uso por {SEGUNDOS_PAUSA} s: {error}")


def registrar_evento(tipo: str, usuario_sub: str | None) -> None:
    """Guarda un evento de uso. Nunca lanza: si falla, la request sigue igual."""

    if en_pausa():
        return

    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO evento_uso (tipo, usuario_sub) VALUES (%s, %s)",
                (tipo, usuario_sub),
            )
        conn.commit()
    except psycopg2.OperationalError as error:
        # Error de conexión (base caída, timeout, conexión cortada)
        _pausar(error)
    except Exception as error:
        print(f"[USO] No se pudo registrar el evento {tipo}: {error}")
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def registro_habilitado() -> bool:
    return os.getenv("REGISTRAR_USO", "1") != "0"


def _registrar_sin_fallar(tipo: str, usuario_sub: str | None) -> None:
    # Corre después de enviar la respuesta: una excepción acá ya no tiene a quién avisarle
    try:
        registrar_evento(tipo, usuario_sub)
    except Exception as error:
        print(f"[USO] No se pudo registrar el evento {tipo}: {error}")


def registrar_si_corresponde(request, response) -> None:
    """Lógica del middleware de main.py.

    Si la request es una funcionalidad contada, agrega el registro como tarea en segundo
    plano de la respuesta: Starlette la corre después de enviarla, así que con la base
    lenta o caída la request no espera. Si la respuesta ya traía una tarea, corren las dos.
    """

    try:
        if not registro_habilitado():
            return

        ruta = request.url.path
        if ruta == "/metrics":
            return

        tipo = clasificar(request.method, ruta, request.query_params, response.status_code)
        if tipo is None:
            return

        usuario_sub = sub_sin_verificar(request.headers.get("authorization"))
        tarea = BackgroundTask(_registrar_sin_fallar, tipo, usuario_sub)

        if response.background is None:
            response.background = tarea
        else:
            response.background = BackgroundTasks(tasks=[response.background, tarea])
    except Exception as error:
        print(f"[USO] Error al registrar el uso: {error}")


# --- Resumen para el administrador ---

def _inicio_del_dia(dia: date) -> datetime:
    return datetime.combine(dia, time(0), ZONA_URUGUAY)


def _dias(desde: date, hasta: date) -> list[date]:
    return [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]


def _existe_tabla(cur, nombre: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (f"public.{nombre}",))
    fila = cur.fetchone()
    return fila is not None and fila[0] is not None


def _serie(conteos: list[tuple]) -> list[dict]:
    return [{"etiqueta": etiqueta, "cantidad": int(cantidad)} for etiqueta, cantidad in conteos]


def armar_resumen(
    desde: date,
    hasta: date,
    total_eventos: int,
    usuarios_distintos: int,
    por_tipo: dict[str, int],
    por_dia: dict[date, int],
    por_estado: dict[str, int],
    por_perfil: dict[str, int],
) -> dict:
    """Arma la respuesta de /api/admin/analisis/uso a partir de los conteos (sin base)."""

    funcionalidades = [
        {"clave": clave, "etiqueta": FUNCIONALIDADES.get(clave, clave), "cantidad": int(cantidad)}
        for clave, cantidad in por_tipo.items()
        if cantidad > 0
    ]
    funcionalidades.sort(key=lambda f: (-f["cantidad"], f["etiqueta"]))

    # Los tres estados siempre; si aparece otro valor en la base, va al final
    estados = [(etiqueta, por_estado.get(clave, 0)) for clave, etiqueta in ESTADOS_USUARIO.items()]
    estados += [
        (clave or SIN_DATO, cantidad)
        for clave, cantidad in sorted(por_estado.items(), key=lambda e: str(e[0]))
        if clave not in ESTADOS_USUARIO
    ]

    perfiles = sorted(
        ((perfil or SIN_DATO, cantidad) for perfil, cantidad in por_perfil.items()),
        key=lambda p: (p[0] == SIN_DATO, -p[1], p[0]),
    )

    return {
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "total_eventos": int(total_eventos),
        "usuarios_distintos": int(usuarios_distintos),
        "busquedas": int(por_tipo.get("busqueda_repositorio", 0)),
        "por_funcionalidad": funcionalidades,
        "por_dia": [
            {"periodo": dia.isoformat(), "cantidad": int(por_dia.get(dia, 0))}
            for dia in _dias(desde, hasta)
        ],
        "usuarios_registrados": {
            "total": int(sum(por_estado.values())),
            "por_estado": _serie(estados),
            "por_perfil": _serie(perfiles),
        },
    }


def resumen_uso(desde: date, hasta: date) -> dict:
    """Uso de la plataforma entre desde y hasta (días de Uruguay, inclusivo). Sin caché."""

    inicio = _inicio_del_dia(desde)
    fin = _inicio_del_dia(hasta + timedelta(days=1))

    total_eventos = 0
    usuarios_distintos = 0
    por_tipo: dict[str, int] = {}
    por_dia: dict[date, int] = {}
    por_estado: dict[str, int] = {}
    por_perfil: dict[str, int] = {}

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # En una base que todavía no corrió ensure_schema, ceros en vez de 500
            if _existe_tabla(cur, "evento_uso"):
                cur.execute(
                    """
                    SELECT COUNT(*), COUNT(DISTINCT usuario_sub)
                    FROM evento_uso
                    WHERE creado >= %s AND creado < %s
                    """,
                    (inicio, fin),
                )
                total_eventos, usuarios_distintos = cur.fetchone()

                cur.execute(
                    """
                    SELECT tipo, COUNT(*)
                    FROM evento_uso
                    WHERE creado >= %s AND creado < %s
                    GROUP BY tipo
                    """,
                    (inicio, fin),
                )
                por_tipo = {tipo: cantidad for tipo, cantidad in cur.fetchall()}

                # INTERVAL y no el texto '-03:00': como texto Postgres lo toma como POSIX
                # e invierte el signo.
                cur.execute(
                    """
                    SELECT (creado AT TIME ZONE INTERVAL '-03:00')::date AS dia, COUNT(*)
                    FROM evento_uso
                    WHERE creado >= %s AND creado < %s
                    GROUP BY dia
                    """,
                    (inicio, fin),
                )
                por_dia = {dia: cantidad for dia, cantidad in cur.fetchall()}

            # Usuarios registrados hoy (no depende del período)
            if _existe_tabla(cur, "usuarios"):
                cur.execute("SELECT estado, COUNT(*) FROM usuarios GROUP BY estado")
                por_estado = {estado: cantidad for estado, cantidad in cur.fetchall()}

                cur.execute(
                    """
                    SELECT NULLIF(TRIM(perfil), ''), COUNT(*)
                    FROM usuarios
                    GROUP BY 1
                    """
                )
                for perfil, cantidad in cur.fetchall():
                    clave = perfil or SIN_DATO
                    por_perfil[clave] = por_perfil.get(clave, 0) + cantidad
    finally:
        conn.close()

    return armar_resumen(
        desde, hasta, total_eventos, usuarios_distintos,
        por_tipo, por_dia, por_estado, por_perfil,
    )
