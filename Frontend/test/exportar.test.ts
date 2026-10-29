import { beforeEach, describe, expect, it, vi } from "vitest";

// Ruta /analisis-datos/exportar (RF006-07) con la sesión y la API simuladas
const estado = vi.hoisted(() => ({
  session: { accessToken: "token" } as Record<string, unknown> | null,
  paths: [] as string[],
  respuesta: null as Response | null,
}));

vi.mock("@/auth", () => ({ auth: async () => estado.session }));
vi.mock("@/lib/api", () => ({
  apiFetch: async (path: string) => {
    estado.paths.push(path);
    return estado.respuesta ?? new Response(JSON.stringify({ disponible: true, total: 0 }), { status: 200 });
  },
}));

// Sin vitest.config no hay alias "@/": se apuntan a los módulos reales
vi.mock("@/lib/analisis", async () => await import("../lib/analisis"));
vi.mock("@/lib/reportes", async () => await import("../lib/reportes"));

import { GET } from "../app/analisis-datos/exportar/route";

function pedir(query: string) {
  const url = new URL(`http://localhost/analisis-datos/exportar?${query}`);
  return GET({ nextUrl: url } as never);
}

beforeEach(() => {
  estado.session = { accessToken: "token" };
  estado.paths = [];
  estado.respuesta = null;
});

describe("exportar", () => {
  it("sin sesión responde 401 y no llama a la API", async () => {
    estado.session = null;
    const r = await pedir("formato=csv&vista=fondos");
    expect(r.status).toBe(401);
    expect(estado.paths).toEqual([]);
  });

  it("con la sesión vencida (error de refresh) responde 401", async () => {
    estado.session = { accessToken: "token", error: "RefreshTokenError" };
    expect((await pedir("formato=csv&vista=fondos")).status).toBe(401);
  });

  it.each([
    "formato=xls&vista=fondos",
    "formato=csv&vista=../admin/usuarios",
    "formato=csv&vista=opciones",
    "formato=csv",
    "vista=fondos",
  ])("rechaza vista o formato fuera de la lista: %s", async (query) => {
    const r = await pedir(query);
    expect(r.status).toBe(400);
    expect(estado.paths).toEqual([]);
  });

  it("arma la URL de la API solo con filtros conocidos y codificados", async () => {
    const r = await pedir(
      "formato=csv&vista=fondos&organismo=A%26vista%3Duso%2F..&tematica=Salud&estado=Inventado&desde=2025-13-01&hasta=2025-12-31&url=http://evil",
    );
    expect(r.status).toBe(200);
    expect(estado.paths).toHaveLength(1);
    const [ruta, query] = estado.paths[0].split("?");
    expect(ruta).toBe("/api/analisis/fondos");
    const params = new URLSearchParams(query);
    expect(Object.fromEntries(params)).toEqual({
      organismo: "A&vista=uso/..",
      tematica: "Salud",
      hasta: "2025-12-31",
    });
  });

  it("uso solo pasa el período a la API de admin", async () => {
    await pedir("formato=csv&vista=uso&organismo=ANII&desde=2026-10-01&hasta=2026-10-10");
    expect(estado.paths).toEqual(["/api/admin/analisis/uso?desde=2026-10-01&hasta=2026-10-10"]);
  });

  it("tendencias lleva la agrupación", async () => {
    await pedir("formato=pdf&vista=tendencias&agrupar=mes");
    expect(estado.paths).toEqual(["/api/analisis/tendencias?agrupar=mes"]);
  });

  it("CSV con nombre de archivo y tipo correctos", async () => {
    const r = await pedir("formato=csv&vista=fondos");
    expect(r.headers.get("Content-Type")).toBe("text/csv; charset=utf-8");
    expect(r.headers.get("Content-Disposition")).toMatch(/^attachment; filename="interfascia-analisis-fondos-\d{4}-\d{2}-\d{2}\.csv"$/);
  });

  it("PDF válido", async () => {
    const r = await pedir("formato=pdf&vista=resumen");
    expect(r.headers.get("Content-Type")).toBe("application/pdf");
    const bytes = new Uint8Array(await r.arrayBuffer());
    expect(new TextDecoder().decode(bytes.slice(0, 5))).toBe("%PDF-");
  });

  it("un 403 de la API (uso sin rol admin) pasa como 403 con el detail", async () => {
    estado.respuesta = new Response(JSON.stringify({ detail: "No tenés permisos para esta acción" }), { status: 403 });
    const r = await pedir("formato=csv&vista=uso");
    expect(r.status).toBe(403);
    expect(await r.text()).toBe("No tenés permisos para esta acción");
  });

  it("un 500 de la API se informa como 502", async () => {
    estado.respuesta = new Response("boom", { status: 500 });
    const r = await pedir("formato=csv&vista=fondos");
    expect(r.status).toBe(502);
  });
});
