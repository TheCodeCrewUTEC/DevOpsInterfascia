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
