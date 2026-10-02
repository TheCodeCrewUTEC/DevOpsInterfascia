#!/bin/bash
# Crea el usuario y la base de datos de Keycloak dentro del Postgres del proyecto.
# Postgres ejecuta los scripts de esta carpeta solo la primera vez (volumen vacío).
# Si el volumen ya existía, crear la base a mano: ver SETUP.md, sección 11.1.
set -euo pipefail

psql -v ON_ERROR_STOP=1 \
     --username "$POSTGRES_USER" \
     --dbname "$POSTGRES_DB" \
     --set usuario="$KEYCLOAK_DB_USER" \
     --set clave="$KEYCLOAK_DB_PASSWORD" \
     --set base="$KEYCLOAK_DB_NAME" <<-'EOSQL'
	CREATE ROLE :"usuario" LOGIN PASSWORD :'clave';
	CREATE DATABASE :"base" OWNER :"usuario";
EOSQL
