#!/usr/bin/env bash
# Crea los roles de realm, actualiza las opciones del perfil de registro y activa
# el listener que deja las cuentas nuevas pendientes de aprobación.
#
# realm-interfascia.json ya trae esta configuración, pero Keycloak solo lo importa
# cuando el realm no existe. Este script aplica lo mismo sobre el realm existente.
#
# Uso (desde la raíz del repo, con el contenedor levantado):
#   bash keycloak/configurar-roles-aprobacion.sh

set -euo pipefail

CONTENEDOR="${KEYCLOAK_CONTAINER:-interfascia-keycloak}"
R=interfascia
CFG=/tmp/kcadm-roles-aprobacion.config

kc() {
  docker exec -i "$CONTENEDOR" /opt/keycloak/bin/kcadm.sh "$@" --config "$CFG"
}

echo "Autenticando en Keycloak..."
docker exec -i "$CONTENEDOR" bash -c '
  /opt/keycloak/bin/kcadm.sh config credentials \
    --server http://localhost:8080 --realm master \
    --user "$KC_BOOTSTRAP_ADMIN_USERNAME" \
    --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" \
    --config '"$CFG"' >/dev/null
'

crear_rol() {
  local nombre="$1"
  local desc="$2"
  if kc get "roles/$nombre" -r "$R" >/dev/null 2>&1; then
    echo "Rol $nombre ya existe."
  else
    echo "Creando rol $nombre..."
    kc create roles -r "$R" -s "name=$nombre" -s "description=$desc" >/dev/null
  fi
}

crear_rol admin "Administrador: acceso total y gestion de permisos"
crear_rol gestor_innovacion "Gestor/a de innovacion: acceso a analitica de datos"
crear_rol investigador "Investigador/a: consultas IA"
crear_rol emprendedor "Emprendedor/a / Empresario/a: demandas al foro"

echo "Activando listener registration-approval..."
kc update "realms/$R" -s eventsEnabled=true -s 'eventsListeners=["jboss-logging","registration-approval"]'

echo "Actualizando perfil de usuario..."
COMP_ID=$(kc get components -r "$R" -q name=declarative-user-profile --fields id --format csv --noquotes | head -n1)
if [ -z "$COMP_ID" ]; then
  echo "AVISO: no se encontro el UserProfileProvider; actualiza el perfil desde la consola admin."
else
  TMP_DIR=$(mktemp -d)
  kc get "components/$COMP_ID" -r "$R" > "$TMP_DIR/component.json"

  python - "$TMP_DIR/component.json" <<'PY'
import json, sys

path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    comp = json.load(f)

profile = json.loads(comp["config"]["kc.user.profile.config"][0])
attrs = {a["name"]: a for a in profile["attributes"]}

roles_perfil = [
    "Administrador",
    "Gestor/a de innovación",
    "Investigador/a",
    "Emprendedor/a / Empresario/a",
    "Otros",
]

attrs["perfil"] = {
    "name": "perfil",
    "displayName": "${perfil}",
    "validations": {"options": {"options": roles_perfil}},
    "permissions": {"view": ["admin", "user"], "edit": ["admin", "user"]},
    "multivalued": False,
    "required": {"roles": ["user"]},
}
attrs["perfilOtro"] = {
    "name": "perfilOtro",
    "displayName": "${perfilOtro}",
    "validations": {"length": {"max": 255}},
    "permissions": {"view": ["admin", "user"], "edit": ["admin", "user"]},
    "multivalued": False,
}
attrs["estadoAprobacion"] = {
    "name": "estadoAprobacion",
    "displayName": "${estadoAprobacion}",
    "permissions": {"view": ["admin"], "edit": ["admin"]},
    "multivalued": False,
}

orden = [
    "username", "firstName", "lastName", "email",
    "departamentoResidencia", "departamentosActuacion", "celular",
    "instituciones", "perfil", "perfilOtro", "estadoAprobacion",
]
profile["attributes"] = [attrs[n] for n in orden if n in attrs]
comp["config"]["kc.user.profile.config"] = [
    json.dumps(profile, ensure_ascii=False, separators=(",", ": "))
]

with open(path, "w", encoding="utf-8") as f:
    json.dump(comp, f, ensure_ascii=False)
PY

  docker cp "$TMP_DIR/component.json" "$CONTENEDOR:/tmp/user-profile-component.json"
  kc update "components/$COMP_ID" -r "$R" -f /tmp/user-profile-component.json
  docker exec -i "$CONTENEDOR" rm -f /tmp/user-profile-component.json
  rm -rf "$TMP_DIR"
  echo "Perfil de usuario actualizado."
fi

docker exec -i "$CONTENEDOR" rm -f "$CFG"
echo "Listo. Las cuentas nuevas quedan deshabilitadas hasta que un admin las habilite en Keycloak."
