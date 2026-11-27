from app.services import usuario_service


def test_registro_sin_estado_queda_pendiente(monkeypatch):
    llamadas = {}

    def obtener_usuario(keycloak_id):
        return {"id": keycloak_id, "enabled": True, "attributes": {}}

    def cambiar_aprobacion(keycloak_id, habilitado, estado):
        llamadas["cambio"] = (keycloak_id, habilitado, estado)

    def importar(keycloak_id, usuario=None):
        llamadas["importar"] = (keycloak_id, usuario)
        return {"keycloak_id": keycloak_id, "estado": "pendiente"}

    monkeypatch.setattr(usuario_service.keycloak, "obtener_usuario", obtener_usuario)
    monkeypatch.setattr(usuario_service.keycloak, "cambiar_aprobacion", cambiar_aprobacion)
    monkeypatch.setattr(usuario_service, "importar_desde_keycloak", importar)

    guardado = usuario_service.registrar_desde_keycloak("kc-1")

    assert llamadas["cambio"] == ("kc-1", False, "pendiente")
    _id, importado = llamadas["importar"]
    assert _id == "kc-1"
    assert importado["enabled"] is False
    assert importado["attributes"]["estadoAprobacion"] == ["pendiente"]
    assert guardado["estado"] == "pendiente"


def test_registro_con_estado_no_se_pisa(monkeypatch):
    usuario = {
        "id": "kc-2",
        "enabled": True,
        "attributes": {"estadoAprobacion": ["aprobado"]},
    }
    llamadas = {}

    def cambiar_aprobacion(*args):
        llamadas["cambio"] = args

    def importar(keycloak_id, usuario_kc=None):
        llamadas["importar"] = (keycloak_id, usuario_kc)
        return {"keycloak_id": keycloak_id, "estado": "aprobado"}

    monkeypatch.setattr(usuario_service.keycloak, "obtener_usuario", lambda _id: usuario)
    monkeypatch.setattr(usuario_service.keycloak, "cambiar_aprobacion", cambiar_aprobacion)
    monkeypatch.setattr(usuario_service, "importar_desde_keycloak", importar)

    usuario_service.registrar_desde_keycloak("kc-2")

    assert "cambio" not in llamadas
    assert llamadas["importar"] == ("kc-2", usuario)


def test_incorpora_cuentas_de_keycloak_que_no_estan_en_la_tabla(monkeypatch):
    guardados = []

    monkeypatch.setattr(usuario_service, "ids_en_tabla", lambda: {"ya-esta"})
    monkeypatch.setattr(usuario_service.keycloak, "rol_de_usuario", lambda _id: None)

    def guardar(datos, actualizar_estado=False):
        guardados.append((datos, actualizar_estado))
        return datos

    monkeypatch.setattr(usuario_service, "guardar_usuario", guardar)

    agregados = usuario_service.incorporar_faltantes([
        {
            "id": "ya-esta",
            "enabled": True,
            "email": "ana@example.com",
            "attributes": {"estadoAprobacion": ["aprobado"]},
        },
        {
            "id": "nuevo",
            "enabled": True,
            "email": "nuevo@example.com",
            "firstName": "Nuevo",
            "attributes": {},
        },
        {
            "id": "deshabilitado",
            "enabled": False,
            "email": "off@example.com",
            "attributes": {},
        },
    ])

    assert agregados == 2
    assert [datos["keycloak_id"] for datos, _ in guardados] == ["nuevo", "deshabilitado"]
    assert guardados[0][0]["estado"] == "aprobado"
    assert guardados[1][0]["estado"] == "pendiente"
    assert all(actualizar for _, actualizar in guardados)
