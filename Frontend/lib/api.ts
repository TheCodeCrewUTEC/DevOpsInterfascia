import { auth } from "@/auth";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

// Llama a la API de FastAPI desde el servidor, con el token de Keycloak si hay sesión.
// Uso: const res = await apiFetch("/api/auth/me");
export async function apiFetch(path: string, init: RequestInit = {}) {
  const session = await auth();
  const headers = new Headers(init.headers);

  if (session?.accessToken && !session.error) {
    headers.set("Authorization", `Bearer ${session.accessToken}`);
  }

  return fetch(`${API_URL}${path}`, { ...init, headers });
}
