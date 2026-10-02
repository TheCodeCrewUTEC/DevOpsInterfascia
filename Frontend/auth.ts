import NextAuth from "next-auth";
import type { JWT } from "next-auth/jwt";
import Keycloak from "next-auth/providers/keycloak";

// ============================================================
// KEYCLOAK
// ============================================================

export const keycloakIssuer =
  process.env.AUTH_KEYCLOAK_ISSUER ??
  "https://auth.interfasciauy.com/realms/interfascia";

const clientId =
  process.env.AUTH_KEYCLOAK_ID ??
  "interfascia-frontend";

const clientSecret =
  process.env.AUTH_KEYCLOAK_SECRET;

const tokenUrl =
  `${keycloakIssuer}/protocol/openid-connect/token`;

const userinfoUrl =
  `${keycloakIssuer}/protocol/openid-connect/userinfo`;


// ============================================================
// REFRESH TOKEN
// ============================================================

async function refreshAccessToken(token: JWT): Promise<JWT> {
  try {
    const response = await fetch(tokenUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        grant_type: "refresh_token",
        client_id: clientId,
        client_secret: clientSecret ?? "",
        refresh_token: token.refreshToken ?? "",
      }),
    });

    const tokens = await response.json();

    if (!response.ok) {
      throw tokens;
    }

    return {
      ...token,
      accessToken: tokens.access_token,
      refreshToken:
        tokens.refresh_token ?? token.refreshToken,
      idToken:
        tokens.id_token ?? token.idToken,
      expiresAt:
        Math.floor(Date.now() / 1000) + tokens.expires_in,
      error: undefined,
    };
  } catch (error) {
    console.error(
      "Error al renovar el token de Keycloak",
      error
    );

    return {
      ...token,
      error: "RefreshTokenError",
    };
  }
}


// ============================================================
// NEXT AUTH
// ============================================================

export const {
  handlers,
  auth,
  signIn,
  signOut,
} = NextAuth({

  providers: [
    Keycloak({
      clientId,
      clientSecret,

      // Issuer público de Keycloak
      issuer: keycloakIssuer,

      authorization: {
        url:
          `${keycloakIssuer}/protocol/openid-connect/auth`,
        params: {
          scope: "openid email profile",
          ui_locales: "es",
        },
      },

      // Endpoint público
      token: tokenUrl,

      // Endpoint público
      userinfo: userinfoUrl,
    }),
  ],

  pages: {
    signIn: "/login",
    error: "/login",
  },

  callbacks: {

    async jwt({ token, account }) {

      // Primer login
      if (account) {
        return {
          ...token,
          accessToken: account.access_token,
          refreshToken: account.refresh_token,
          idToken: account.id_token,
          expiresAt: account.expires_at,
        };
      }

      // Token todavía válido
      if (
        token.expiresAt &&
        Date.now() <
          (token.expiresAt - 30) * 1000
      ) {
        return token;
      }

      // Token vencido
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