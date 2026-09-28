import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { NextRequest } from "next/server";
import { signIn } from "@/auth";
import { safeRedirect } from "@/lib/safe-redirect";

const COOKIE_REINTENTO = "ifx-auth-reintento";

// El formulario de login lo muestra Keycloak; esta ruta solo redirige
export async function GET(request: NextRequest) {
  const { searchParams, origin } = request.nextUrl;

  // Auth.js vuelve acá cuando falla el callback. El caso típico es haber empezado dos logins
  // en el mismo navegador (otra pestaña, botón atrás): la cookie PKCE ya no coincide.
  // Keycloak igual dejó la sesión abierta, así que un reintento entra sin pedir nada.
  // Solo reintentamos una vez para no entrar en un bucle si el error es de configuración.
  if (searchParams.has("error")) {
    const cookieStore = await cookies();

    if (cookieStore.has(COOKIE_REINTENTO)) {
      cookieStore.delete(COOKIE_REINTENTO);
      redirect(`/?authError=${encodeURIComponent(searchParams.get("error") ?? "")}`);
    }

    cookieStore.set(COOKIE_REINTENTO, "1", { httpOnly: true, sameSite: "lax", maxAge: 60, path: "/" });
  }

  await signIn("keycloak", {
    redirectTo: safeRedirect(searchParams.get("callbackUrl"), origin),
  });
}
