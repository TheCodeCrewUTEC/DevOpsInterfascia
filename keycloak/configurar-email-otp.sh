#!/usr/bin/env bash
# Activa el segundo factor por correo (autenticador email-otp) en un realm que ya existe.
#
# realm-interfascia.json ya trae esta configuración, pero Keycloak solo lo importa cuando el
# realm no existe (si ya está en la base, "Import skipped"). Este script aplica lo mismo sobre
# el realm existente. Se puede correr varias veces.
#
# Uso (desde la raíz del repo, con el contenedor levantado):
#   bash keycloak/configurar-email-otp.sh
#
# Las credenciales de admin y de SMTP se toman del entorno del contenedor (docker-compose / .env),
# así no pasan por la línea de comandos del host.

set -euo pipefail

CONTENEDOR="${KEYCLOAK_CONTAINER:-interfascia-keycloak}"

docker exec -i "$CONTENEDOR" bash -s <<'SCRIPT'
set -euo pipefail

R=interfascia
FLUJO=browser-email-otp
FORMS=browser-email-otp-forms
CFG=/tmp/kcadm-email-otp.config

kc() { /opt/keycloak/bin/kcadm.sh "$@" --config "$CFG"; }

kc config credentials --server http://localhost:8080 --realm master \
  --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null

# Agrega un autenticador a un flujo y le pone el requisito
agregar() { # flujo provider requisito
  local id
  id=$(kc create "authentication/flows/$1/executions/execution" -r "$R" -s "provider=$2" -i)
  kc update "authentication/flows/$1/executions" -r "$R" -b "{\"id\":\"$id\",\"requirement\":\"$3\"}"
}

if kc get authentication/flows -r "$R" --fields alias --format csv --noquotes | grep -qx "$FLUJO"; then
  echo "El flujo $FLUJO ya existe, no se modifica."
else
  echo "Creando el flujo $FLUJO..."
  kc create authentication/flows -r "$R" -s alias="$FLUJO" -s providerId=basic-flow \
    -s topLevel=true -s builtIn=false -s "description=Navegador: usuario y contraseña + código por correo" >/dev/null

  agregar "$FLUJO" auth-cookie ALTERNATIVE
  agregar "$FLUJO" identity-provider-redirector ALTERNATIVE

  kc create "authentication/flows/$FLUJO/executions/flow" -r "$R" -s alias="$FORMS" \
    -s type=basic-flow -s provider=registration-page-form \
    -s "description=Usuario y contraseña, después el código enviado al correo" >/dev/null
  id_forms=$(kc get "authentication/flows/$FLUJO/executions" -r "$R" --fields id,displayName --format csv --noquotes \
    | grep ",$FORMS\$" | cut -d, -f1)
  kc update "authentication/flows/$FLUJO/executions" -r "$R" -b "{\"id\":\"$id_forms\",\"requirement\":\"ALTERNATIVE\"}"

  agregar "$FORMS" auth-username-password-form REQUIRED
  agregar "$FORMS" email-otp REQUIRED
fi

echo "Usando $FLUJO como flujo de login y el tema de correo interfascia..."
kc update "realms/$R" -s browserFlow="$FLUJO" -s emailTheme=interfascia

if [ -n "${SMTP_USER:-}" ] && [ -n "${SMTP_PASSWORD:-}" ]; then
  echo "Configurando SMTP ($SMTP_HOST:$SMTP_PORT como $SMTP_USER)..."
  kc update "realms/$R" \
    -s "smtpServer.host=$SMTP_HOST" -s "smtpServer.port=$SMTP_PORT" \
    -s "smtpServer.from=${SMTP_FROM:-$SMTP_USER}" -s "smtpServer.fromDisplayName=Interfascia" \
    -s "smtpServer.auth=true" -s "smtpServer.starttls=true" -s "smtpServer.ssl=false" \
    -s "smtpServer.user=$SMTP_USER" -s "smtpServer.password=$SMTP_PASSWORD"
else
  echo "AVISO: faltan SMTP_USER / SMTP_PASSWORD en el .env; sin SMTP no se pueden enviar los códigos."
fi

rm -f "$CFG"
echo "Listo."
SCRIPT
