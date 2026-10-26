from datetime import date

from app.services import deteccion_alertas_service as d

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


# --- Vigencia y visibilidad ---

def test_es_vigente():
    assert d.es_vigente(convocatoria(estado="Cerrada"), HOY) is False
    assert d.es_vigente(convocatoria(estado="cerrado"), HOY) is False
    assert d.es_vigente(convocatoria(fecha_cierre=date(2026, 10, 24)), HOY) is False
    assert d.es_vigente(convocatoria(fecha_cierre=None), HOY) is True
    assert d.es_vigente(convocatoria(fecha_cierre=HOY), HOY) is True


def test_es_visible_pide_descripcion_y_alguna_fecha():
    assert d.es_visible(convocatoria()) is True
    assert d.es_visible(convocatoria(descripcion="   ")) is False
    assert d.es_visible(convocatoria(fecha_apertura=None, fecha_cierre=None)) is False
    assert d.es_visible(convocatoria(fecha_apertura=None)) is True


def test_foto_normaliza():
    f = d.foto(convocatoria(titulo="  Fondo   de\nenergía ", requisitos="", fecha_cierre="2026-11-30"))
    assert f["titulo"] == "Fondo de energía"
    assert f["requisitos"] is None
    assert f["fecha_apertura"] == "2026-10-01"
    assert f["fecha_cierre"] == "2026-11-30"


# --- Cambios ---

def test_completar_un_campo_vacio_no_es_cambio():
    assert d.cambios_relevantes(convocatoria(requisitos=None), convocatoria(requisitos="Ser pyme")) == []


def test_cambio_de_estado_es_cambio():
    cambios = d.cambios_relevantes(convocatoria(), convocatoria(estado="Cerrada"))
    assert cambios == [{"campo": "estado", "antes": "Abierta", "despues": "Cerrada"}]


def test_espacios_distintos_no_son_cambio():
    assert d.cambios_relevantes(
        convocatoria(), convocatoria(descripcion="Apoyo  a proyectos\nde Energía renovable ")
    ) == []


def test_cambio_de_fecha_contra_foto_guardada():
    guardada = seguimiento_de(convocatoria())[1]["datos"]
    cambios = d.cambios_relevantes(guardada, convocatoria(fecha_cierre=date(2026, 12, 15)))
    assert cambios == [{"campo": "fecha_cierre", "antes": "2026-11-30", "despues": "2026-12-15"}]


# --- Coincidencias ---

def test_coincide_tematica_sin_tildes():
    f = d.foto(convocatoria())
    assert d.coincide({"tipo": "tematica", "valor": "energia"}, f)
    assert d.coincide({"tipo": "tematica", "valor": "Energía"}, f)
    assert not d.coincide({"tipo": "tematica", "valor": "Salud"}, f)


def test_coincide_institucion_parcial():
    f = d.foto(convocatoria())
    assert d.coincide({"tipo": "institucion", "valor": "agencia nacional"}, f)
    assert not d.coincide({"tipo": "institucion", "valor": "INIA"}, f)


def test_coincide_convocatoria_por_id():
    f = d.foto(convocatoria())
    assert d.coincide({"tipo": "convocatoria", "convocatoria_id": 1}, f)
    assert not d.coincide({"tipo": "convocatoria", "convocatoria_id": 2}, f)


# --- Claves y mensajes ---

def test_claves_dedup_estables():
    f = convocatoria()
    assert d.clave_apertura(f) == "apertura:1:2026-10-01:2026-11-30"
    assert d.clave_apertura(convocatoria(fecha_apertura=None, fecha_cierre=None)) == "apertura:1:sf:sf"
    assert d.clave_cierre(f) == "cierre:1:2026-11-30"

    cambios = [{"campo": "estado", "antes": "Abierta", "despues": "Cerrada"}]
    clave = d.clave_actualizacion(1, cambios)
    assert clave == d.clave_actualizacion(1, [dict(reversed(list(cambios[0].items())))])
    assert clave.startswith("actualizacion:1:") and len(clave.split(":")[2]) == 16
    assert clave != d.clave_actualizacion(1, [{"campo": "estado", "antes": "Abierta", "despues": "Suspendida"}])


def test_armar_mensaje():
    f = convocatoria()

    titulo, mensaje = d.armar_mensaje("apertura", f)
    assert titulo == "Nueva convocatoria: Fondo de energía solar"
    assert "Cierre: 30/11/2026" in mensaje

    assert d.armar_mensaje("cierre", f, dias=0)[0] == "Cierra hoy: Fondo de energía solar"
    assert d.armar_mensaje("cierre", f, dias=1)[0] == "Cierra en 1 día: Fondo de energía solar"
    titulo, mensaje = d.armar_mensaje("cierre", f, dias=5)
    assert titulo == "Cierra en 5 días: Fondo de energía solar"
    assert "30/11/2026" in mensaje

    cambios = [
        {"campo": "estado", "antes": "Abierta", "despues": "Cerrada"},
        {"campo": "descripcion", "antes": "x" * 500, "despues": "corta"},
    ]
    titulo, mensaje = d.armar_mensaje("actualizacion", f, cambios=cambios)
    assert titulo == "Actualización en Fondo de energía solar"
    lineas = mensaje.split("\n")
    assert lineas[0] == "Estado: Abierta → Cerrada"
    assert len(lineas[1]) < 250 and lineas[1].endswith("→ corta")


# --- Planificación ---

SUSCRIPCION_TEMATICA = {"usuario_sub": "ana", "tipo": "tematica", "convocatoria_id": None, "valor": "Energía"}


def test_primera_corrida_solo_toma_fotos():
    fotos, notificaciones = d.planificar(
        [convocatoria(), convocatoria(id=2, descripcion=None)], {}, [SUSCRIPCION_TEMATICA], {}, HOY
    )
    assert notificaciones == []
    assert [(id, notificada) for id, _, notificada in fotos] == [(1, True), (2, False)]


def test_apertura_nueva_notifica_al_suscriptor_de_tematica():
    existente = convocatoria(id=9, titulo="Otra", descripcion="Salud")
    fotos, notificaciones = d.planificar(
        [existente, convocatoria()],
        seguimiento_de(existente),
        [SUSCRIPCION_TEMATICA, {"usuario_sub": "beto", "tipo": "tematica", "valor": "Salud"}],
        {},
        HOY,
    )
    assert len(notificaciones) == 1
    n = notificaciones[0]
    assert (n["usuario_sub"], n["tipo"], n["convocatoria_id"]) == ("ana", "apertura", 1)
    assert n["clave_dedup"] == "apertura:1:2026-10-01:2026-11-30"
    # Solo se guarda la foto nueva; la que no cambió no se reescribe
    assert [(id, notificada) for id, _, notificada in fotos] == [(1, True)]


def test_apertura_cuando_se_completa_la_descripcion():
    sin_datos = convocatoria(descripcion=None, fecha_apertura=None, fecha_cierre=None)
    _, notificaciones = d.planificar(
        [convocatoria()], seguimiento_de(sin_datos, notificada=False), [SUSCRIPCION_TEMATICA], {}, HOY
    )
    assert [n["tipo"] for n in notificaciones] == ["apertura"]


def test_no_duplica_si_ya_se_notifico_la_apertura():
    _, notificaciones = d.planificar(
        [convocatoria()], seguimiento_de(convocatoria()), [SUSCRIPCION_TEMATICA], {}, HOY
    )
    assert notificaciones == []


def test_preferencia_apertura_apagada_no_notifica():
    _, notificaciones = d.planificar(
        [convocatoria()],
        seguimiento_de(convocatoria(id=9)),
        [SUSCRIPCION_TEMATICA],
        {"ana": {"alerta_apertura": False}},
        HOY,
    )
    assert notificaciones == []


def test_un_usuario_con_varias_suscripciones_recibe_una_sola_apertura():
    _, notificaciones = d.planificar(
        [convocatoria()],
        seguimiento_de(convocatoria(id=9)),
        [SUSCRIPCION_TEMATICA, {"usuario_sub": "ana", "tipo": "institucion", "valor": "Agencia"}],
        {},
        HOY,
    )
    assert len(notificaciones) == 1


def test_actualizacion_solo_a_suscriptores_de_la_convocatoria():
    anterior = convocatoria()
    _, notificaciones = d.planificar(
        [convocatoria(estado="Cerrada")],
        seguimiento_de(anterior),
        [
            SUSCRIPCION_TEMATICA,
            {"usuario_sub": "beto", "tipo": "convocatoria", "convocatoria_id": 1, "valor": None},
            {"usuario_sub": "caro", "tipo": "convocatoria", "convocatoria_id": 1, "valor": None},
        ],
        {"caro": {"alerta_actualizacion": False}},
        HOY,
    )
    assert [(n["usuario_sub"], n["tipo"]) for n in notificaciones] == [("beto", "actualizacion")]
    assert notificaciones[0]["detalle"] == [{"campo": "estado", "antes": "Abierta", "despues": "Cerrada"}]


def test_planificar_cierres():
    def fila(id, dias, **extra):
        return {"usuario_sub": "ana", **convocatoria(id=id, fecha_cierre=date.fromordinal(HOY.toordinal() + dias), **extra)}

    filas = [fila(1, 0), fila(2, 7), fila(3, 8), fila(4, 3, estado="Cerrada"), fila(5, -1)]
    notificaciones = d.planificar_cierres(filas, {"ana": {"dias_anticipacion_cierre": 7}}, HOY)

    assert [n["convocatoria_id"] for n in notificaciones] == [1, 2]
    assert notificaciones[0]["titulo"].startswith("Cierra hoy:")
    assert notificaciones[1]["detalle"] == {"dias_restantes": 7, "fecha_cierre": "2026-11-01"}
    assert notificaciones[1]["clave_dedup"] == "cierre:2:2026-11-01"


def test_planificar_cierres_respeta_preferencia_y_default():
    fila = {"usuario_sub": "ana", **convocatoria(fecha_cierre=date(2026, 10, 30))}
    assert len(d.planificar_cierres([fila], {}, HOY)) == 1
    assert d.planificar_cierres([fila], {"ana": {"alerta_cierre": False}}, HOY) == []
    assert d.planificar_cierres([fila], {"ana": {"dias_anticipacion_cierre": 3}}, HOY) == []
