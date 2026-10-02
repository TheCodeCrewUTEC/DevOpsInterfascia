import { NextResponse, type NextRequest } from "next/server";

export const dynamic = "force-dynamic";

function withSetCookies(existing: string, setCookies: string[]) {
  const jar = new Map<string, string>();

  for (const part of existing.split(";").map((item) => item.trim()).filter(Boolean)) {
    const separator = part.indexOf("=");
    if (separator > 0) jar.set(part.slice(0, separator), part.slice(separator + 1));
  }

  for (const setCookie of setCookies) {
    const pair = setCookie.split(";")[0] ?? "";
    const separator = pair.indexOf("=");
    if (separator > 0) jar.set(pair.slice(0, separator).trim(), pair.slice(separator + 1).trim());
  }

  return [...jar.entries()].map(([name, value]) => `${name}=${value}`).join("; ");
}

function setCookiesOf(response: Response) {
  return response.headers.getSetCookie?.() ?? [];
}

// Abre el formulario de registro de Keycloak, no la pantalla de login.
// El endpoint /registrations usa el mismo código OAuth, así que al terminar
// Auth.js vuelve a /registro/exitoso.
export async function GET(request: NextRequest) {
  const origin = request.nextUrl.origin;
  const cookie = request.headers.get("cookie") ?? "";

  const csrfResponse = await fetch(new URL("/api/auth/csrf", origin), {
    headers: { cookie },
    cache: "no-store",
  });
  const csrfPayload = (await csrfResponse.json()) as { csrfToken?: string };
  const csrfCookies = setCookiesOf(csrfResponse);

  if (!csrfPayload.csrfToken) {
    return NextResponse.redirect(new URL("/login", origin));
  }

  const signInResponse = await fetch(new URL("/api/auth/signin/keycloak", origin), {
    method: "POST",
    redirect: "manual",
    cache: "no-store",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "X-Auth-Return-Redirect": "1",
      cookie: withSetCookies(cookie, csrfCookies),
      Origin: origin,
    },
    body: new URLSearchParams({
      csrfToken: csrfPayload.csrfToken,
      callbackUrl: "/registro/exitoso",
    }),
  });

  const payload = (await signInResponse.json().catch(() => null)) as { url?: string } | null;
  const authUrl = payload?.url ?? signInResponse.headers.get("location");

  if (!authUrl) {
    return NextResponse.redirect(new URL("/login", origin));
  }

  const registrationUrl = authUrl.replace(
    "/protocol/openid-connect/auth",
    "/protocol/openid-connect/registrations",
  );

  const response = NextResponse.redirect(registrationUrl);
  for (const setCookie of [...csrfCookies, ...setCookiesOf(signInResponse)]) {
    response.headers.append("set-cookie", setCookie);
  }
  return response;
}
