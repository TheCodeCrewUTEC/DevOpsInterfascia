import hashlib
import json
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone

from psycopg2.extras import Json

from app.database.connection import get_connection
from app.services import email_service
from app.services.alerta_service import PREFERENCIAS_POR_DEFECTO

# Detección de aperturas, actualizaciones y cierres (RF005-03, 04, 05, 07).
# El scraping corre fuera de Docker y solo inserta/actualiza filas de convocatoria, así
# que los cambios se detectan comparando contra la última foto guardada en
# convocatoria_seguimiento. Lo de arriba es lógica pura (testeable sin base); las
# funciones del final leen y escriben en Postgres y las llama el cron del worker.

# Uruguay no tiene horario de verano: UTC-3 fijo
ZONA_URUGUAY = timezone(timedelta(hours=-3))

CAMPOS_SEGUIMIENTO = (
    "titulo",
    "institucion",
    "estado",
    "fecha_apertura",
    "fecha_cierre",
    "descripcion",
    "beneficiarios",
    "requisitos",
    "financiamiento",
)
COLUMNAS_CONVOCATORIA = "id, " + ", ".join(CAMPOS_SEGUIMIENTO)

ETIQUETAS = {
    "titulo": "Título",
    "institucion": "Institución",
    "estado": "Estado",
    "fecha_apertura": "Fecha de apertura",
    "fecha_cierre": "Fecha de cierre",
    "descripcion": "Descripción",
    "beneficiarios": "Beneficiarios",
    "requisitos": "Requisitos",
    "financiamiento": "Financiamiento",
}

PREFERENCIA_POR_TIPO = {
    "apertura": "alerta_apertura",
    "cierre": "alerta_cierre",
    "actualizacion": "alerta_actualizacion",
}

LARGO_MAXIMO = 200
LARGO_DETALLE = 500
PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Claves de pg_advisory_lock: evitan que el cron y el endpoint admin corran a la vez
BLOQUEO_REVISION = 5005
BLOQUEO_CORREOS = 5006


def hoy_uruguay() -> date:
    return datetime.now(ZONA_URUGUAY).date()


def _texto(valor) -> str | None:
    if valor is None:
        return None
    texto = " ".join(str(valor).split())
    return texto or None


def _fecha(valor) -> date | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError:
        return None


def foto(fila: dict) -> dict:
    """Versión comparable de una convocatoria: fechas ISO, espacios colapsados, vacío → None."""

    datos = {"id": fila.get("id")}

    for campo in CAMPOS_SEGUIMIENTO:
        valor = fila.get(campo)
        if campo.startswith("fecha_"):
            fecha = _fecha(valor)
            datos[campo] = fecha.isoformat() if fecha else None
        else:
            datos[campo] = _texto(valor)

    return datos


def es_visible(f: dict) -> bool:
    """Mismo filtro que el listado de convocatoria_service: descripción y alguna fecha."""

    return bool(_texto(f.get("descripcion"))) and (
        _fecha(f.get("fecha_apertura")) is not None
        or _fecha(f.get("fecha_cierre")) is not None
    )


def es_vigente(f: dict, hoy: date) -> bool:
    estado = (_texto(f.get("estado")) or "").lower()
    if estado.startswith("cerrad"):
        return False

    cierre = _fecha(f.get("fecha_cierre"))
    return cierre is None or cierre >= hoy


def cambios_relevantes(anterior: dict, actual: dict) -> list[dict]:
    """Cambios que vale la pena avisar. Completar un campo que estaba vacío no cuenta:
    es el script que rellena los NULL después del scraping, no una novedad."""

    cambios = []
    anterior = foto(anterior)
    actual = foto(actual)

    for campo in CAMPOS_SEGUIMIENTO:
        antes = anterior[campo]
        despues = actual[campo]

        if antes is None or antes == despues:
            continue

        cambios.append({"campo": campo, "antes": antes, "despues": despues})

    return cambios


def normalizar(texto) -> str:
    """Minúsculas, sin tildes y con espacios colapsados."""

    descompuesto = unicodedata.normalize("NFD", str(texto or ""))
    sin_tildes = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return " ".join(sin_tildes.lower().split())


def coincide(suscripcion: dict, f: dict) -> bool:
    tipo = suscripcion.get("tipo")

    if tipo == "convocatoria":
        return suscripcion.get("convocatoria_id") is not None and suscripcion["convocatoria_id"] == f.get("id")

    valor = normalizar(suscripcion.get("valor"))
    if not valor:
        return False

    if tipo == "institucion":
        texto = f.get("institucion")
    elif tipo == "tematica":
        texto = " ".join(
            f.get(campo) or "" for campo in ("titulo", "descripcion", "beneficiarios")
        )
    else:
        return False

    # Palabra o frase completa: "UTE" no coincide con "UTEC" ni "Salud" con "saludable"
    patron = rf"(?<!\w){re.escape(valor)}(?!\w)"
    return re.search(patron, normalizar(texto)) is not None


def clave_apertura(f: dict) -> str:
    # Incluye el cierre: una reapertura que extiende el plazo es un aviso nuevo. Si solo
    # cambia el estado (Cerrada → Abierta con las mismas fechas) la clave se repite y no
    # se vuelve a avisar: suele ser el scraper corrigiendo el estado, no otra edición.
    datos = foto(f)
    return f"apertura:{f['id']}:{datos['fecha_apertura'] or 'sf'}:{datos['fecha_cierre'] or 'sf'}"


def clave_cierre(f: dict) -> str:
    return f"cierre:{f['id']}:{foto(f)['fecha_cierre']}"


def clave_actualizacion(id: int, cambios: list[dict]) -> str:
    serializado = json.dumps(cambios, sort_keys=True, ensure_ascii=False)
    return f"actualizacion:{id}:{hashlib.sha1(serializado.encode('utf-8')).hexdigest()[:16]}"


def _truncar(texto, largo: int = LARGO_MAXIMO) -> str:
    texto = _texto(texto) or "—"
    return texto if len(texto) <= largo else texto[: largo - 1].rstrip() + "…"


def detalle_cambios(cambios: list[dict]) -> list[dict]:
    """Lo que se guarda en notificacion.detalle: los textos largos (descripción,
    requisitos) se recortan para no copiar la convocatoria entera en cada aviso."""

    return [
        {
            **c,
            "antes": c["antes"] if c["antes"] is None else _truncar(c["antes"], LARGO_DETALLE),
            "despues": c["despues"] if c["despues"] is None else _truncar(c["despues"], LARGO_DETALLE),
        }
        for c in cambios
    ]


def _fecha_legible(valor) -> str | None:
    fecha = _fecha(valor)
    return fecha.strftime("%d/%m/%Y") if fecha else None


def _valor_legible(campo: str, valor) -> str:
    if campo.startswith("fecha_"):
        return _fecha_legible(valor) or "—"
    return _truncar(valor)


def armar_mensaje(tipo: str, f: dict, cambios: list[dict] | None = None, dias: int | None = None) -> tuple[str, str]:
    nombre = _truncar(f.get("titulo") or f"Convocatoria #{f.get('id')}")

    if tipo == "apertura":
        lineas = ["Se publicó una convocatoria que coincide con tus alertas."]
        if f.get("institucion"):
            lineas.append(f"Institución: {_truncar(f['institucion'])}")
        if _fecha_legible(f.get("fecha_apertura")):
            lineas.append(f"Apertura: {_fecha_legible(f['fecha_apertura'])}")
        if _fecha_legible(f.get("fecha_cierre")):
            lineas.append(f"Cierre: {_fecha_legible(f['fecha_cierre'])}")
        return f"Nueva convocatoria: {nombre}", "\n".join(lineas)

    if tipo == "cierre":
        if dias == 0:
            titulo = f"Cierra hoy: {nombre}"
        elif dias == 1:
            titulo = f"Cierra en 1 día: {nombre}"
        else:
            titulo = f"Cierra en {dias} días: {nombre}"
        return titulo, f"La convocatoria cierra el {_fecha_legible(f.get('fecha_cierre'))}."

    lineas = [
        f"{ETIQUETAS.get(c['campo'], c['campo'])}: "
        f"{_valor_legible(c['campo'], c['antes'])} → {_valor_legible(c['campo'], c['despues'])}"
        for c in cambios or []
    ]
    return f"Actualización en {nombre}", "\n".join(lineas)


def _preferencia(preferencias: dict, usuario_sub: str, clave: str):
    valor = (preferencias.get(usuario_sub) or {}).get(clave)
    return PREFERENCIAS_POR_DEFECTO[clave] if valor is None else valor


def _notificacion(usuario_sub: str, tipo: str, f: dict, clave: str, detalle, **extra) -> dict:
    titulo, mensaje = armar_mensaje(tipo, f, **extra)
    return {
        "usuario_sub": usuario_sub,
        "tipo": tipo,
        "convocatoria_id": f["id"],
        "titulo": titulo,
        "mensaje": mensaje,
        "detalle": detalle,
        "clave_dedup": clave,
    }


def planificar(
    convocatorias: list[dict],
    seguimiento: dict,
    suscripciones: list[dict],
    preferencias: dict,
    hoy: date,
) -> tuple[list[tuple], list[dict]]:
    """Compara las convocatorias actuales con las fotos guardadas.

    seguimiento: {convocatoria_id: {"datos": foto, "apertura_notificada": bool}}
    preferencias: {usuario_sub: fila de preferencia_notificacion}; sin fila → por defecto.
    Devuelve (fotos a guardar como (id, datos, apertura_notificada), notificaciones a crear).
    """

    fotos = []
    notificaciones = []
    inicial = not seguimiento

    for fila in convocatorias:
        actual = foto(fila)
        id = actual["id"]
        datos = {campo: actual[campo] for campo in CAMPOS_SEGUIMIENTO}
        anterior = seguimiento.get(id)

        # Primera corrida: solo se toma la foto. Lo que ya está publicado cuenta como avisado.
        if inicial:
            fotos.append((id, datos, es_visible(actual) and es_vigente(actual, hoy)))
            continue

        notificada = bool(anterior and anterior.get("apertura_notificada"))

        if anterior is not None and notificada:
            # El scraper reutiliza la fila (por título) para una nueva edición del mismo
            # fondo: si cambió la fecha de apertura o la foto anterior ya no estaba vigente,
            # la apertura se vuelve a avisar a quienes siguen la institución o la temática.
            previa = foto({"id": id, **(anterior.get("datos") or {})})
            if (
                previa["fecha_apertura"] is not None
                and previa["fecha_apertura"] != actual["fecha_apertura"]
            ) or not es_vigente(previa, hoy):
                notificada = False

        if anterior is not None:
            cambios = cambios_relevantes(anterior.get("datos") or {}, actual)

            if cambios:
                clave = clave_actualizacion(id, cambios)
                detalle = detalle_cambios(cambios)
                avisados = set()
                for s in suscripciones:
                    usuario = s["usuario_sub"]
                    if (
                        s.get("tipo") == "convocatoria"
                        and coincide(s, actual)
                        and usuario not in avisados
                        and _preferencia(preferencias, usuario, "alerta_actualizacion")
                    ):
                        avisados.add(usuario)
                        notificaciones.append(
                            _notificacion(usuario, "actualizacion", actual, clave, detalle, cambios=cambios)
                        )

        if not notificada and es_visible(actual) and es_vigente(actual, hoy):
            notificada = True
            clave = clave_apertura(actual)
            detalle = {
                "fecha_apertura": actual["fecha_apertura"],
                "fecha_cierre": actual["fecha_cierre"],
            }
            avisados = set()
            for s in suscripciones:
                usuario = s["usuario_sub"]
                if (
                    usuario not in avisados
                    and coincide(s, actual)
                    and _preferencia(preferencias, usuario, "alerta_apertura")
                ):
                    avisados.add(usuario)
                    notificaciones.append(_notificacion(usuario, "apertura", actual, clave, detalle))

        # Solo se reescriben las fotos que cambiaron
        if (
            anterior is None
            or (anterior.get("datos") or {}) != datos
            or bool(anterior.get("apertura_notificada")) != notificada
        ):
            fotos.append((id, datos, notificada))

    return fotos, notificaciones


def planificar_cierres(suscripciones_con_conv: list[dict], preferencias: dict, hoy: date) -> list[dict]:
    """suscripciones_con_conv: una fila por suscripción tipo 'convocatoria', con usuario_sub
    y las columnas de la convocatoria (id, titulo, estado, fecha_cierre, ...)."""

    notificaciones = []
    vistas = set()

    for fila in suscripciones_con_conv:
        usuario = fila["usuario_sub"]
        f = foto(fila)
        cierre = _fecha(f["fecha_cierre"])

        if cierre is None or (usuario, f["id"]) in vistas:
            continue
        if not es_vigente(f, hoy) or not _preferencia(preferencias, usuario, "alerta_cierre"):
            continue

        dias = (cierre - hoy).days
        if not 0 <= dias <= int(_preferencia(preferencias, usuario, "dias_anticipacion_cierre")):
            continue

        vistas.add((usuario, f["id"]))
        detalle = {"dias_restantes": dias, "fecha_cierre": f["fecha_cierre"]}
        notificaciones.append(_notificacion(usuario, "cierre", f, clave_cierre(f), detalle, dias=dias))

    return notificaciones


# --- Con base de datos ---

def _filas(cur) -> list[dict]:
    columnas = [col[0] for col in cur.description]
    return [dict(zip(columnas, row)) for row in cur.fetchall()]


def _leer_preferencias(cur) -> dict:
    cur.execute(
        """
        SELECT usuario_sub, alerta_apertura, alerta_cierre, alerta_actualizacion,
               dias_anticipacion_cierre
        FROM preferencia_notificacion
        """
    )
    return {fila["usuario_sub"]: fila for fila in _filas(cur)}


def _insertar_notificaciones(cur, notificaciones: list[dict]) -> dict:
    """Devuelve cuántas se crearon de cada tipo; las repetidas las descarta clave_dedup."""

    creadas = {}

    for n in notificaciones:
        cur.execute(
            """
            INSERT INTO notificacion
                (usuario_sub, tipo, convocatoria_id, titulo, mensaje, detalle, clave_dedup)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (usuario_sub, clave_dedup) DO NOTHING
            """,
            (
                n["usuario_sub"],
                n["tipo"],
                n["convocatoria_id"],
                n["titulo"],
                n["mensaje"],
                Json(n["detalle"]) if n["detalle"] is not None else None,
                n["clave_dedup"],
            )
        )
        creadas[n["tipo"]] = creadas.get(n["tipo"], 0) + cur.rowcount

    return creadas


def revisar_convocatorias() -> dict:
    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(%s)", (BLOQUEO_REVISION,))

                cur.execute(f"SELECT {COLUMNAS_CONVOCATORIA} FROM convocatoria ORDER BY id")
                convocatorias = _filas(cur)

                cur.execute(
                    "SELECT convocatoria_id, datos, apertura_notificada FROM convocatoria_seguimiento"
                )
                seguimiento = {
                    fila["convocatoria_id"]: fila for fila in _filas(cur)
                }

                cur.execute("SELECT usuario_sub, tipo, convocatoria_id, valor FROM suscripcion")
                suscripciones = _filas(cur)
                preferencias = _leer_preferencias(cur)

                fotos, notificaciones = planificar(
                    convocatorias, seguimiento, suscripciones, preferencias, hoy_uruguay()
                )

                for id, datos, notificada in fotos:
                    cur.execute(
                        """
                        INSERT INTO convocatoria_seguimiento (convocatoria_id, datos, apertura_notificada)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (convocatoria_id) DO UPDATE SET
                            datos = EXCLUDED.datos,
                            apertura_notificada = EXCLUDED.apertura_notificada,
                            actualizado = NOW()
                        """,
                        (id, Json(datos), notificada)
                    )

                creadas = _insertar_notificaciones(cur, notificaciones)
    finally:
        conn.close()

    return {
        "inicial": not seguimiento,
        "aperturas": creadas.get("apertura", 0),
        "actualizaciones": creadas.get("actualizacion", 0),
        "nuevas": sum(1 for c in convocatorias if c["id"] not in seguimiento),
    }


def avisar_cierres() -> dict:
    conn = get_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT s.usuario_sub, {", ".join("c." + c for c in COLUMNAS_CONVOCATORIA.split(", "))}
                    FROM suscripcion s
                    JOIN convocatoria c ON c.id = s.convocatoria_id
                    WHERE s.tipo = 'convocatoria' AND c.fecha_cierre IS NOT NULL
                    """
                )
                filas = _filas(cur)
                preferencias = _leer_preferencias(cur)

                notificaciones = planificar_cierres(filas, preferencias, hoy_uruguay())
                creadas = _insertar_notificaciones(cur, notificaciones)
    finally:
        conn.close()

    return {"cierres": creadas.get("cierre", 0)}


def enviar_correos_pendientes(limite: int = 50) -> dict:
    """Manda por correo las notificaciones de quienes lo habilitaron (opt-in), solo las
    creadas desde que lo habilitaron. Cada fila se marca (enviada o con el error) después
    de intentar el envío, con un commit por fila. Si el proceso se corta entre el envío y
    el UPDATE, ese correo puede salir de nuevo en la próxima corrida: se prefiere un
    duplicado ocasional a perder correos."""

    if not email_service.configurado():
        print("[ALERTAS] SMTP no configurado: no se envían correos")
        return {"omitido": "smtp no configurado"}

    resultado = {"enviados": 0, "fallidos": 0, "omitidos": 0}
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", (BLOQUEO_CORREOS,))
            if not cur.fetchone()[0]:
                conn.rollback()
                return resultado

            # La tabla usuarios la crea el backend; el worker puede correr antes
            cur.execute("SELECT to_regclass('public.usuarios') IS NOT NULL")
            hay_usuarios = cur.fetchone()[0]
            correo_usuario = "u.email" if hay_usuarios else "NULL"
            join_usuarios = (
                "LEFT JOIN usuarios u ON u.keycloak_id = n.usuario_sub" if hay_usuarios else ""
            )

            cur.execute(
                f"""
                SELECT n.id, n.tipo, n.convocatoria_id, n.titulo, n.mensaje, n.detalle,
                       COALESCE(NULLIF(btrim(p.email), ''), {correo_usuario}) AS correo
                FROM notificacion n
                JOIN preferencia_notificacion p ON p.usuario_sub = n.usuario_sub
                {join_usuarios}
                WHERE p.email_habilitado
                  AND p.email_habilitado_desde IS NOT NULL
                  AND n.creado >= p.email_habilitado_desde
                  AND n.email_enviado_en IS NULL
                  AND NOT n.eliminada
                  AND n.email_intentos < 3
                  AND CASE n.tipo
                        WHEN 'apertura' THEN p.alerta_apertura
                        WHEN 'cierre' THEN p.alerta_cierre
                        ELSE p.alerta_actualizacion
                      END
                ORDER BY n.creado, n.id
                LIMIT %s
                """,
                (limite,)
            )
            pendientes = _filas(cur)
            conn.commit()

            for n in pendientes:
                correo = (n["correo"] or "").strip()
                error = None

                if not PATRON_EMAIL.match(correo):
                    error = "Sin correo válido"
                    resultado["omitidos"] += 1
                else:
                    try:
                        asunto, texto, html = email_service.cuerpo_notificacion(n)
                        email_service.enviar_correo(correo, asunto, texto, html)
                        resultado["enviados"] += 1
                    except Exception as e:
                        error = str(e)[:500] or e.__class__.__name__
                        resultado["fallidos"] += 1
                        print(f"[ALERTAS] Error enviando notificación {n['id']}: {error}")

                if error is None:
                    cur.execute(
                        "UPDATE notificacion SET email_enviado_en = NOW(), email_error = NULL WHERE id = %s",
                        (n["id"],)
                    )
                else:
                    cur.execute(
                        """
                        UPDATE notificacion
                        SET email_intentos = email_intentos + 1, email_error = %s
                        WHERE id = %s
                        """,
                        (error, n["id"])
                    )
                conn.commit()

            cur.execute("SELECT pg_advisory_unlock(%s)", (BLOQUEO_CORREOS,))
            conn.commit()
    finally:
        conn.close()

    return resultado
