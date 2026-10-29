"""Casos borde de RF005 que no cubrían los tests del programador: envío de correos con
base falsa (reintentos, sin correo válido, advisory lock), zona horaria y detección.
No usan Postgres ni SMTP reales."""

from datetime import date, datetime, timezone

import pytest

from app.services import deteccion_alertas_service as d
from app.services import email_service

HOY = date(2026, 10, 25)


def convocatoria(**cambios):
    base = {
        "id": 1,
        "titulo": "Fondo de energía solar",
        "institucion": "Agencia Nacional de Investigación e Innovación",
        "estado": "Abierta",
        "fecha_apertura": date(2026, 10, 1),
        "fecha_cierre": date(2026, 11, 30),
        "descripcion": "Apoyo a proyectos de Energía renovable",
        "beneficiarios": "Empresas",
        "requisitos": None,
        "financiamiento": None,
    }
    base.update(cambios)
    return base


def seguimiento_de(*filas, notificada=True):
    return {
        f["id"]: {
            "datos": {c: d.foto(f)[c] for c in d.CAMPOS_SEGUIMIENTO},
            "apertura_notificada": notificada,
        }
        for f in filas
    }


# --- Zona horaria ---

class _Reloj(datetime):
    ahora_utc = datetime(2026, 10, 26, 1, 30, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz=None):
        return cls.ahora_utc.astimezone(tz)


def test_hoy_uruguay_antes_de_medianoche_local(monkeypatch):
    # 01:30 UTC del 26 son las 22:30 del 25 en Uruguay
    monkeypatch.setattr(d, "datetime", _Reloj)
    assert d.hoy_uruguay() == date(2026, 10, 25)


def test_cierre_hoy_es_dia_cero_y_ayer_no_avisa():
    filas = [
        {"usuario_sub": "u", **convocatoria(id=1, fecha_cierre=HOY)},
        {"usuario_sub": "u", **convocatoria(id=2, fecha_cierre=date(2026, 10, 24))},
    ]
    notificaciones = d.planificar_cierres(filas, {}, HOY)

    assert [(n["convocatoria_id"], n["detalle"]["dias_restantes"]) for n in notificaciones] == [(1, 0)]
    assert notificaciones[0]["titulo"].startswith("Cierra hoy")


def test_cierre_fuera_de_la_anticipacion_elegida():
    filas = [{"usuario_sub": "u", **convocatoria(fecha_cierre=date(2026, 11, 5))}]  # 11 días
    assert d.planificar_cierres(filas, {"u": {"dias_anticipacion_cierre": 10}}, HOY) == []
    assert len(d.planificar_cierres(filas, {"u": {"dias_anticipacion_cierre": 11}}, HOY)) == 1


# --- Detección ---

def test_convocatoria_nueva_cerrada_no_notifica_apertura():
    vieja = convocatoria(id=1)
    nueva = convocatoria(id=2, estado="Cerrada")
    suscripciones = [{"usuario_sub": "u", "tipo": "tematica", "valor": "Energía", "convocatoria_id": None}]

    fotos, notificaciones = d.planificar([vieja, nueva], seguimiento_de(vieja), suscripciones, {}, HOY)

    assert notificaciones == []
    # Queda la foto sin marcar: si se reabre, se avisa
    assert (2, {c: d.foto(nueva)[c] for c in d.CAMPOS_SEGUIMIENTO}, False) in fotos


def test_actualizacion_con_preferencia_apagada_no_notifica():
    anterior = convocatoria()
    actual = convocatoria(fecha_cierre=date(2026, 12, 15))
    suscripciones = [{"usuario_sub": "u", "tipo": "convocatoria", "convocatoria_id": 1, "valor": None}]

    _, notificaciones = d.planificar(
        [actual], seguimiento_de(anterior), suscripciones, {"u": {"alerta_actualizacion": False}}, HOY
    )

    assert notificaciones == []


def test_nueva_edicion_en_la_misma_fila_avisa_apertura_por_interes():
    edicion_anterior = convocatoria(
        fecha_apertura=date(2025, 3, 1), fecha_cierre=date(2025, 4, 1)
    )
    nueva_edicion = convocatoria(fecha_apertura=date(2026, 10, 20), fecha_cierre=date(2026, 12, 1))
    suscripciones = [{"usuario_sub": "u", "tipo": "tematica", "valor": "Energía", "convocatoria_id": None}]

    _, notificaciones = d.planificar([nueva_edicion], seguimiento_de(edicion_anterior), suscripciones, {}, HOY)

    assert [n["tipo"] for n in notificaciones] == ["apertura"]


def test_institucion_coincide_sin_tildes():
    s = {"tipo": "institucion", "valor": "Agencia Nacional de Investigacion", "convocatoria_id": None}
    assert d.coincide(s, convocatoria())


def test_institucion_coincide_por_palabra_completa():
    ute = {"tipo": "institucion", "valor": "UTE", "convocatoria_id": None}
    assert not d.coincide(ute, convocatoria(institucion="UTEC"))
    assert d.coincide(ute, convocatoria(institucion="UTE - Administración Nacional de Usinas"))

    investigacion = {"tipo": "institucion", "valor": "Investigación", "convocatoria_id": None}
    assert d.coincide(investigacion, convocatoria())
    assert not d.coincide({"tipo": "institucion", "valor": "Agencia Nac", "convocatoria_id": None}, convocatoria())


def test_tematica_coincide_por_palabra_completa():
    salud = {"tipo": "tematica", "valor": "Salud", "convocatoria_id": None}
    assert not d.coincide(salud, convocatoria(descripcion="Alimentación saludable en escuelas"))
    assert d.coincide(salud, convocatoria(descripcion="Proyectos de salud pública"))
    assert d.coincide(
        {"tipo": "tematica", "valor": "energia renovable", "convocatoria_id": None}, convocatoria()
    )


def test_reapertura_cerrada_a_abierta_avisa_apertura():
    cerrada = convocatoria(estado="Cerrada")
    suscripciones = [{"usuario_sub": "u", "tipo": "institucion", "valor": "ANII Agencia", "convocatoria_id": None},
                     {"usuario_sub": "v", "tipo": "tematica", "valor": "Energía", "convocatoria_id": None}]

    fotos, notificaciones = d.planificar([convocatoria()], seguimiento_de(cerrada), suscripciones, {}, HOY)

    assert [(n["usuario_sub"], n["tipo"]) for n in notificaciones] == [("v", "apertura")]
    # Mismas fechas → misma clave: si ya se había avisado esa edición, la base lo descarta
    assert notificaciones[0]["clave_dedup"] == "apertura:1:2026-10-01:2026-11-30"
    assert fotos[0][2] is True


def test_cierre_vencido_que_se_extiende_avisa_apertura_con_clave_nueva():
    vencida = convocatoria(fecha_cierre=date(2026, 10, 20))
    extendida = convocatoria(fecha_cierre=date(2026, 12, 20))
    suscripciones = [{"usuario_sub": "u", "tipo": "tematica", "valor": "Energía", "convocatoria_id": None}]

    _, notificaciones = d.planificar([extendida], seguimiento_de(vencida), suscripciones, {}, HOY)

    assert [n["tipo"] for n in notificaciones] == ["apertura"]
    assert notificaciones[0]["clave_dedup"] != d.clave_apertura(vencida)


def test_completar_fecha_de_apertura_no_repite_la_apertura():
    sin_apertura = convocatoria(fecha_apertura=None)
    suscripciones = [{"usuario_sub": "u", "tipo": "tematica", "valor": "Energía", "convocatoria_id": None}]

    fotos, notificaciones = d.planificar([convocatoria()], seguimiento_de(sin_apertura), suscripciones, {}, HOY)

    assert notificaciones == []
    assert fotos[0][2] is True


def test_convocatoria_que_vence_queda_lista_para_reabrir_sin_avisar():
    vencida = convocatoria(fecha_cierre=date(2026, 10, 20))
    suscripciones = [{"usuario_sub": "u", "tipo": "tematica", "valor": "Energía", "convocatoria_id": None}]

    fotos, notificaciones = d.planificar([vencida], seguimiento_de(vencida), suscripciones, {}, HOY)

    assert notificaciones == []
    assert [(id, notificada) for id, _, notificada in fotos] == [(1, False)]


def test_detalle_de_actualizacion_recorta_textos_largos():
    anterior = convocatoria(descripcion="a" * 800)
    actual = convocatoria(descripcion="b" * 800)
    suscripciones = [{"usuario_sub": "u", "tipo": "convocatoria", "convocatoria_id": 1, "valor": None}]

    _, notificaciones = d.planificar([actual], seguimiento_de(anterior), suscripciones, {}, HOY)

    cambio = notificaciones[0]["detalle"][0]
    assert len(cambio["antes"]) == 500 and cambio["antes"].endswith("…")
    assert len(cambio["despues"]) == 500 and cambio["despues"].endswith("…")
    # La clave se calcula con el texto completo, no con el recortado
    assert notificaciones[0]["clave_dedup"] == d.clave_actualizacion(
        1, [{"campo": "descripcion", "antes": "a" * 800, "despues": "b" * 800}]
    )


# --- Envío de correos con base falsa ---

class CursorCorreos:
    def __init__(self, base):
        self.base = base
        self.description = None
        self._resultado = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, parametros=None):
        self.base.sentencias.append((" ".join(sql.split()), parametros))
        if "pg_try_advisory_lock" in sql:
            self._resultado = [(self.base.lock_libre,)]
        elif "to_regclass" in sql:
            self._resultado = [(True,)]
        elif sql.lstrip().startswith("SELECT n.id"):
            self.description = [(c,) for c in ("id", "tipo", "convocatoria_id", "titulo", "mensaje", "detalle", "correo")]
            self._resultado = self.base.pendientes
        else:
            self._resultado = []

    def fetchone(self):
        return self._resultado[0] if self._resultado else None

    def fetchall(self):
        return list(self._resultado)


class BaseCorreos:
    def __init__(self, pendientes, lock_libre=True):
        self.pendientes = pendientes
        self.lock_libre = lock_libre
        self.sentencias = []
        self.cerrada = False
        self.commits = 0

    def cursor(self):
        return CursorCorreos(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass

    def close(self):
        self.cerrada = True

    def con(self, texto):
        return [p for s, p in self.sentencias if texto in s]


@pytest.fixture
def smtp(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "alertas@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "clave")
    enviados = []
    monkeypatch.setattr(email_service, "enviar_correo", lambda dest, asunto, texto, html=None: enviados.append(dest))
    return enviados


def _usar(monkeypatch, base):
    monkeypatch.setattr(d, "get_connection", lambda: base)


def test_correos_envia_marca_y_libera_lock(monkeypatch, smtp):
    base = BaseCorreos([(1, "apertura", 5, "T", "M", None, " ana@example.com ")])
    _usar(monkeypatch, base)

    assert d.enviar_correos_pendientes() == {"enviados": 1, "fallidos": 0, "omitidos": 0}
    assert smtp == ["ana@example.com"]
    assert base.con("SET email_enviado_en = NOW()") == [(1,)]
    assert base.con("pg_advisory_unlock") == [(d.BLOQUEO_CORREOS,)]
    assert base.cerrada


def test_correos_sin_correo_valido_suma_intento_sin_enviar(monkeypatch, smtp):
    base = BaseCorreos([(2, "cierre", 5, "T", "M", None, "no-es-un-correo"), (3, "cierre", 5, "T", "M", None, None)])
    _usar(monkeypatch, base)

    assert d.enviar_correos_pendientes() == {"enviados": 0, "fallidos": 0, "omitidos": 2}
    assert smtp == []
    assert base.con("email_intentos = email_intentos + 1") == [("Sin correo válido", 2), ("Sin correo válido", 3)]


def test_correos_fallo_smtp_guarda_error_y_sigue_con_el_resto(monkeypatch, smtp):
    llamadas = []

    def enviar(dest, *args, **kwargs):
        llamadas.append(dest)
        if dest == "falla@example.com":
            raise OSError("conexión rechazada")

    monkeypatch.setattr(email_service, "enviar_correo", enviar)
    base = BaseCorreos([
        (4, "apertura", 5, "T", "M", None, "falla@example.com"),
        (5, "apertura", 5, "T", "M", None, "ok@example.com"),
    ])
    _usar(monkeypatch, base)

    assert d.enviar_correos_pendientes() == {"enviados": 1, "fallidos": 1, "omitidos": 0}
    assert llamadas == ["falla@example.com", "ok@example.com"]
    assert base.con("email_intentos = email_intentos + 1") == [("conexión rechazada", 4)]


def test_correos_consulta_limita_intentos_y_opt_in(monkeypatch, smtp):
    base = BaseCorreos([])
    _usar(monkeypatch, base)
    d.enviar_correos_pendientes(limite=7)

    consulta, parametros = next((s, p) for s, p in base.sentencias if s.startswith("SELECT n.id"))
    assert "n.email_intentos < 3" in consulta
    assert "n.creado >= p.email_habilitado_desde" in consulta
    assert "p.email_habilitado" in consulta
    assert "NOT n.eliminada" in consulta
    assert parametros == (7,)


def test_correos_con_lock_ocupado_no_consulta_ni_envia(monkeypatch, smtp):
    base = BaseCorreos([(1, "apertura", 5, "T", "M", None, "ana@example.com")], lock_libre=False)
    _usar(monkeypatch, base)

    assert d.enviar_correos_pendientes() == {"enviados": 0, "fallidos": 0, "omitidos": 0}
    assert smtp == []
    assert not any(s.startswith("SELECT n.id") for s, _ in base.sentencias)
    assert base.cerrada
