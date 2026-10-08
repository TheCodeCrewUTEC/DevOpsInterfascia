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

echo "Aplicando politica de contrasenas..."
# Minimo 12 caracteres, 3 de 4 categorias (mayuscula, minuscula, numero, especial; ver
# ComplejidadPasswordPolicyProvider del modulo email-otp) y distinta del usuario/mail
kc update "realms/$R" -s 'passwordPolicy=length(12) and complejidad(3) and notUsername(undefined) and notEmail(undefined)'

echo "Activando proteccion contra fuerza bruta..."
# 5 intentos fallidos bloquean la cuenta 15 minutos; un admin puede desbloquearla antes
kc update "realms/$R" -s bruteForceProtected=true -s permanentLockout=false -s failureFactor=5   -s waitIncrementSeconds=900 -s maxFailureWaitSeconds=900 -s maxDeltaTimeSeconds=43200   -s minimumQuickLoginWaitSeconds=60 -s quickLoginCheckMilliSeconds=1000

echo "Dando 1 hora para completar el inicio de sesion..."
# Pasado ese tiempo con la página de login abierta, Keycloak reinicia el login ("tardó demasiado")
kc update "realms/$R" -s accessCodeLifespanLogin=3600

echo "Activando listener registration-approval..."
kc update "realms/$R" -s eventsEnabled=true -s 'eventsListeners=["jboss-logging","registration-approval"]'

echo "Configurando cliente interfascia-backend (cuenta de servicio de la API)..."
# Login directo habilitado: la API verifica la contraseña actual cuando el usuario la cambia
# El secreto se lee del entorno del contenedor para no pasarlo por la línea de comandos
if ! docker exec -i "$CONTENEDOR" bash -c '[ -n "$KEYCLOAK_BACKEND_CLIENT_SECRET" ]'; then
  echo "ERROR: el contenedor no tiene KEYCLOAK_BACKEND_CLIENT_SECRET (revisá el .env y recreá keycloak)."
  exit 1
fi
BACKEND_ID=$(kc get clients -r "$R" -q clientId=interfascia-backend --fields id --format csv --noquotes | tr -d '\r' | head -n1)
if [ -z "$BACKEND_ID" ]; then
  docker exec -i "$CONTENEDOR" bash -c '/opt/keycloak/bin/kcadm.sh create clients -r '"$R"' --config '"$CFG"' \
    -s clientId=interfascia-backend -s "name=Interfascia API (cuenta de servicio)" \
    -s publicClient=false -s clientAuthenticatorType=client-secret -s serviceAccountsEnabled=true \
    -s standardFlowEnabled=false -s directAccessGrantsEnabled=true -s implicitFlowEnabled=false \
    -s "secret=$KEYCLOAK_BACKEND_CLIENT_SECRET" >/dev/null'
  echo "Cliente interfascia-backend creado."
else
  # Mantiene el secreto igual al del .env (por si se cambió)
  docker exec -i "$CONTENEDOR" bash -c '/opt/keycloak/bin/kcadm.sh update clients/'"$BACKEND_ID"' -r '"$R"' --config '"$CFG"' \
    -s serviceAccountsEnabled=true -s directAccessGrantsEnabled=true -s "secret=$KEYCLOAK_BACKEND_CLIENT_SECRET"'
  echo "Cliente interfascia-backend ya existía: secreto actualizado."
fi
kc add-roles -r "$R" --uusername service-account-interfascia-backend --cclientid realm-management \
  --rolename view-users --rolename query-users --rolename manage-users
echo "Permisos de usuarios asignados a la cuenta de servicio."

echo "Actualizando perfil de usuario..."
# En Keycloak 26 el perfil se lee y se escribe por el endpoint users/profile.
# Va por tuberías (sin archivos temporales) porque en Git Bash el Python de Windows
# no entiende las rutas /tmp de mktemp.
ACTUALIZAR_PERFIL=$(cat <<'PY'
import io, json, sys

profile = json.load(io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8"))

attrs = {a["name"]: a for a in profile["attributes"]}

# Administrador no se ofrece en el registro: el rol admin se asigna a mano
roles_perfil = [
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
# Los atributos que no están en la lista (agregados después) se conservan al final
profile["attributes"] = [attrs[n] for n in orden if n in attrs] + [
    a for n, a in attrs.items() if n not in orden
]

sys.stdout.buffer.write(json.dumps(profile, ensure_ascii=False).encode("utf-8"))
PY
)

kc get users/profile -r "$R" | python -c "$ACTUALIZAR_PERFIL" | kc update users/profile -r "$R" -f -
echo "Perfil de usuario actualizado."

docker exec -i "$CONTENEDOR" rm -f "$CFG"
echo "Listo. Las cuentas nuevas quedan deshabilitadas hasta que un admin las habilite en Keycloak."
