import type { Session } from "next-auth";

type ClaimsToken = { sub?: string; realm_access?: { roles?: string[] } };

// Lee los claims del access token de Keycloak.
// Solo sirve para decidir qué mostrar: la API vuelve a validar el token y el rol.
function claimsDeSesion(session: Session | null): ClaimsToken {
  const token = session?.accessToken;

  if (!token || session?.error) {
    return {};
  }

  try {
    return JSON.parse(
      Buffer.from(token.split(".")[1], "base64url").toString("utf8"),
    ) as ClaimsToken;
  } catch {
    return {};
  }
}

export function rolesDeSesion(session: Session | null): string[] {
  return claimsDeSesion(session).realm_access?.roles ?? [];
}

function tieneAlguno(session: Session | null, permitidos: string[]) {
  const roles = rolesDeSesion(session);
  return permitidos.some((rol) => roles.includes(rol));
}

export function esAdmin(session: Session | null) {
  return tieneAlguno(session, ["admin"]);
}

// Consultor IA: investigador, gestor de innovación y admin.
export function puedeConsultarIa(session: Session | null) {
  return tieneAlguno(session, ["investigador", "gestor_innovacion", "admin"]);
}

// Análisis de datos y métricas de uso. El investigador y el emprendedor no entran.
export function puedeVerAnalisis(session: Session | null) {
  return tieneAlguno(session, ["gestor_innovacion", "admin"]);
}

// Id del usuario en Keycloak
export function idDeSesion(session: Session | null): string | null {
  return claimsDeSesion(session).sub ?? null;
}
