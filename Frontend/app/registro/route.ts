import type { NextRequest } from "next/server";
import { signIn } from "@/auth";
import { safeRedirect } from "@/lib/safe-redirect";

// prompt=create hace que Keycloak abra directamente el formulario de registro
export async function GET(request: NextRequest) {
  const { searchParams, origin } = request.nextUrl;

  await signIn(
    "keycloak",
    { redirectTo: safeRedirect(searchParams.get("callbackUrl"), origin) },
    { prompt: "create" },
  );
}
