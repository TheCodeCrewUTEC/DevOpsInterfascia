import type { Session } from "next-auth";

// Lee los roles de realm del access token de Keycloak.
// Solo sirve para decidir qué mostrar: la API vuelve a validar el token y el rol.
export function rolesDeSesion(session: Session | null): string[] {
  const token = session?.accessToken;

  if (!token || session?.error) {
    return [];
  }

  try {
    const payload = JSON.parse(
      Buffer.from(token.split(".")[1], "base64url").toString("utf8"),
    ) as { realm_access?: { roles?: string[] } };

    return payload.realm_access?.roles ?? [];
  } catch {
    return [];
  }
}

export function esAdmin(session: Session | null) {
  return rolesDeSesion(session).includes("admin");
}
