"use server";

import { redirect } from "next/navigation";
import { auth, keycloakIssuer, signOut } from "@/auth";

// Cierra la sesión en la app y también en Keycloak
export async function cerrarSesion() {
  const session = await auth();

  await signOut({ redirect: false });

  const logoutUrl = new URL(`${keycloakIssuer}/protocol/openid-connect/logout`);
  logoutUrl.searchParams.set(
    "post_logout_redirect_uri",
    process.env.AUTH_URL ?? "http://localhost:3000",
  );

  if (session?.idToken) {
    logoutUrl.searchParams.set("id_token_hint", session.idToken);
  } else {
    logoutUrl.searchParams.set("client_id", process.env.AUTH_KEYCLOAK_ID ?? "interfascia-frontend");
  }

  redirect(logoutUrl.toString());
}
