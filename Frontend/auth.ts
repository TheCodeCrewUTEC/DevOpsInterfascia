import NextAuth from "next-auth";
import type { JWT } from "next-auth/jwt";
import Keycloak from "next-auth/providers/keycloak";

// URL pública del realm: la usa el navegador y es el "iss" de los tokens
export const keycloakIssuer =
  process.env.AUTH_KEYCLOAK_ISSUER ?? "http://localhost:8080/realms/interfascia";

// Dentro de Docker el frontend no llega a localhost:8080, llega a keycloak:8080
const keycloakInternalIssuer =
  process.env.KEYCLOAK_INTERNAL_ISSUER ?? keycloakIssuer;

const clientId = process.env.AUTH_KEYCLOAK_ID ?? "interfascia-frontend";
const clientSecret = process.env.AUTH_KEYCLOAK_SECRET;

const tokenUrl = `${keycloakInternalIssuer}/protocol/openid-connect/token`;

// Renueva el access token (dura 5 minutos) usando el refresh token.
// Devuelve null si la sesión de Keycloak venció: Auth.js borra la sesión y el usuario queda deslogueado.
async function refreshAccessToken(token: JWT): Promise<JWT | null> {
  if (!token.refreshToken) {
    return null;
  }

  try {
    const response = await fetch(tokenUrl, {
      method: "POST",
      body: new URLSearchParams({
        grant_type: "refresh_token",
        client_id: clientId,
        client_secret: clientSecret ?? "",
        refresh_token: token.refreshToken,
      }),
    });

    const tokens = await response.json();

    // Refresh token vencido o revocado: es esperable, no es un error del servidor
    if (tokens.error === "invalid_grant" || tokens.error === "invalid_token") {
      return null;
    }

    if (!response.ok) {
      throw new Error(`${tokens.error}: ${tokens.error_description}`);
    }

    return {
      ...token,
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token ?? token.refreshToken,
      idToken: tokens.id_token ?? token.idToken,
      expiresAt: Math.floor(Date.now() / 1000) + tokens.expires_in,
      error: undefined,
    };
  } catch (error) {
    // Keycloak caído o respuesta inesperada: mantenemos la sesión marcada con error
    console.error(
      "Error al renovar el token de Keycloak:",
      error instanceof Error ? error.message : error,
    );
    return { ...token, error: "RefreshTokenError" };
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Keycloak({
      clientId,
      clientSecret,
      issuer: keycloakIssuer,
      authorization: {
        url: `${keycloakIssuer}/protocol/openid-connect/auth`,
        params: { scope: "openid email profile", ui_locales: "es" },
      },
      token: tokenUrl,
      userinfo: `${keycloakInternalIssuer}/protocol/openid-connect/userinfo`,
    }),
  ],
  pages: {
    signIn: "/login",
    // En vez de la pantalla genérica "Server error", /login reintenta una vez
    error: "/login",
  },
  callbacks: {
    async jwt({ token, account }) {
      // Primer login: guardamos los tokens que devuelve Keycloak
      if (account) {
        return {
          ...token,
          accessToken: account.access_token,
          refreshToken: account.refresh_token,
          idToken: account.id_token,
          expiresAt: account.expires_at,
        };
      }

      // Renovamos 30 segundos antes de que venza
      if (token.expiresAt && Date.now() < (token.expiresAt - 30) * 1000) {
        return token;
      }

      return refreshAccessToken(token);
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken;
      session.idToken = token.idToken;
      session.error = token.error;
      return session;
    },
  },
});
