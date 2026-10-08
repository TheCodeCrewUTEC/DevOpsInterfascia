import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";

const API_URL = (process.env.API_URL ?? "http://localhost:8000").replace(/\/$/, "");

// El navegador llama a este mismo sitio (/backend/...).
// Next reenvía al contenedor de la API, que no es visible desde Internet.
function destinoDesde(request: NextRequest) {
  const ruta = request.nextUrl.pathname.replace(/^\/backend\/?/, "");
  const destino = new URL(`${API_URL}/${ruta}`);
  destino.search = request.nextUrl.search;
  return destino;
}

// La API responde el redirect con su hostname interno (backend:80).
// Si ese Location llega al navegador, la página pública responde 404.
async function fetchApi(request: NextRequest, destino: URL) {
  const headers = new Headers();
  const tipo = request.headers.get("content-type");
  const conCuerpo = request.method !== "GET" && request.method !== "HEAD";
  if (tipo && conCuerpo) headers.set("content-type", tipo);

  // El token de Keycloak vive en la sesión del servidor, no en el navegador.
  const session = await auth();
  if (session?.accessToken && !session.error) {
    headers.set("Authorization", `Bearer ${session.accessToken}`);
  }

  let actual = destino;
  let response = await fetch(actual, {
    method: request.method,
    headers,
    body: conCuerpo ? request.body : undefined,
    // @ts-expect-error Node fetch exige duplex al reenviar un body en stream.
    duplex: "half",
    cache: "no-store",
    redirect: "manual",
  });

  for (let salto = 0; salto < 3 && [301, 302, 307, 308].includes(response.status); salto += 1) {
    const location = response.headers.get("location");
    if (!location) break;
    const siguiente = new URL(location, actual);
    const api = new URL(API_URL);
    siguiente.protocol = api.protocol;
    siguiente.host = api.host;
    actual = siguiente;
    response = await fetch(actual, {
      method: request.method,
      headers,
      cache: "no-store",
      redirect: "manual",
    });
  }

  return response;
}

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;

  // /internal/... solo lo usa Keycloak por la red de Docker; no se expone a Internet
  if (path.find(Boolean)?.toLowerCase() === "internal") {
    return NextResponse.json({ detail: "No encontrado." }, { status: 404 });
  }

  try {
    const response = await fetchApi(request, destinoDesde(request));

    const respuestaHeaders = new Headers(response.headers);
    respuestaHeaders.delete("content-encoding");
    respuestaHeaders.delete("content-length");
    respuestaHeaders.delete("transfer-encoding");
    respuestaHeaders.delete("location");

    return new NextResponse(response.body, {
      status: response.status,
      headers: respuestaHeaders,
    });
  } catch {
    return NextResponse.json(
      { detail: "No se pudo conectar con la API." },
      { status: 502 },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const dynamic = "force-dynamic";
