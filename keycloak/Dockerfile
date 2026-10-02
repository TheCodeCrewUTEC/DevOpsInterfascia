# Keycloak con el autenticador email-otp (código de 6 dígitos por correo).
# El plugin se compila acá adentro: no hace falta tener Java ni Maven instalados.

FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /build
COPY email-otp/pom.xml .
RUN mvn -q -B dependency:go-offline
COPY email-otp/src src
RUN mvn -q -B package

# Misma versión que keycloak.version en email-otp/pom.xml
FROM quay.io/keycloak/keycloak:26.4.7
COPY --from=build /build/target/email-otp.jar /opt/keycloak/providers/
