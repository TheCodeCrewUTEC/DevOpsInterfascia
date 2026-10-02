import { keycloakIssuer } from "@/auth";

const appUrl = process.env.AUTH_URL ?? "http://localhost:3000";

// URL para cerrar la sesión en Keycloak y volver a la app.
// "destino" es una ruta de la app, por ejemplo "/" o "/registro/confirmado".
export function urlCierreKeycloak(idToken: string | undefined, destino = "/") {
  const logoutUrl = new URL(`${keycloakIssuer}/protocol/openid-connect/logout`);
  logoutUrl.searchParams.set("post_logout_redirect_uri", new URL(destino, appUrl).toString());

  if (idToken) {
    logoutUrl.searchParams.set("id_token_hint", idToken);
  } else {
    logoutUrl.searchParams.set("client_id", process.env.AUTH_KEYCLOAK_ID ?? "interfascia-frontend");
  }

  return logoutUrl.toString();
}
