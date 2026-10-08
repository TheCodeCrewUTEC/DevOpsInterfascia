import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";

const API_URL = (process.env.API_URL ?? "http://localhost:8000").replace(/\/$/, "");

// El navegador llama a este mismo sitio (/backend/...).
// Next reenvía al contenedor de la API, que no es visible desde Internet.
async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;

  // /internal/... solo lo usa Keycloak por la red de Docker; no se expone a Internet
  if (path.find(Boolean)?.toLowerCase() === "internal") {
    return NextResponse.json({ detail: "No encontrado." }, { status: 404 });
  }

  const slash = request.nextUrl.pathname.endsWith("/") ? "/" : "";
  const destino = new URL(`${API_URL}/${path.join("/")}${slash}`);
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

  // El token de Keycloak vive en la sesión del servidor, no en el navegador:
  // se agrega acá para que la API sepa quién hace el pedido.
  const session = await auth();
  if (session?.accessToken && !session.error) {
    headers.set("Authorization", `Bearer ${session.accessToken}`);
  }

  try {
    const response = await fetch(destino, {
      method: request.method,
      headers,
      cache: "no-store",
      redirect: "manual",
    });
  }

  return response;
}

async function proxy(request: NextRequest) {
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
