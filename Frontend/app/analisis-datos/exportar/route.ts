import type { NextRequest } from "next/server";
import { auth } from "@/auth";
import { apiFetch } from "@/lib/api";
import { leerFiltros, queryDeFiltros } from "@/lib/analisis";
import {
  aCsv,
  aPdf,
  esFormatoReporte,
  esVistaReporte,
  nombreArchivo,
  seccionesReporte,
} from "@/lib/reportes";

export const dynamic = "force-dynamic";

// Exportación del análisis (RF006-07) y de las métricas de uso (RF006-08).
// GET ?formato=csv|pdf&vista=<vista>&<filtros de la URL del análisis>
export async function GET(request: NextRequest) {
  const session = await auth();
  if (!session?.accessToken || session.error) {
    return new Response("Tenés que iniciar sesión para exportar.", { status: 401 });
  }

  const params = request.nextUrl.searchParams;
  const formato = params.get("formato") ?? "";
  const vista = params.get("vista") ?? "";

  if (!esFormatoReporte(formato)) {
    return new Response("Formato inválido: tiene que ser csv o pdf.", { status: 400 });
  }
  if (!esVistaReporte(vista)) {
    return new Response("Vista inválida.", { status: 400 });
  }

  // Mismas reglas que la página: lo inválido se descarta
  const filtros = leerFiltros(Object.fromEntries(params));
  let path: string;
  if (vista === "uso") {
    const query = queryDeFiltros({}, { desde: filtros.desde, hasta: filtros.hasta });
    path = `/api/admin/analisis/uso${query ? `?${query}` : ""}`;
  } else {
    const query = queryDeFiltros(filtros, vista === "tendencias" ? { agrupar: filtros.agrupar } : {});
    path = `/api/analisis/${vista}${query ? `?${query}` : ""}`;
  }

  let response: Response;
  try {
    response = await apiFetch(path, { cache: "no-store" });
  } catch {
    return new Response("No se pudo conectar con la API.", { status: 502 });
  }

  if (!response.ok) {
    // 401/403/400 pasan tal cual, con el detail de la API si lo hay
    const cuerpo = await response.json().catch(() => null);
    const detalle = typeof cuerpo?.detail === "string" ? cuerpo.detail : null;
    const status = [400, 401, 403, 404].includes(response.status) ? response.status : 502;
    return new Response(detalle ?? `No se pudieron cargar los datos (${response.status}).`, {
      status,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }

  const ahora = new Date();
  const reporte = seccionesReporte(vista, await response.json(), filtros, ahora);
  const archivo = nombreArchivo(vista, ahora, formato);
  const cabeceras = {
    "Content-Disposition": `attachment; filename="${archivo}"`,
    "Cache-Control": "no-store",
  };

  if (formato === "csv") {
    return new Response(aCsv(reporte), {
      headers: { ...cabeceras, "Content-Type": "text/csv; charset=utf-8" },
    });
  }

  return new Response(aPdf(reporte), {
    headers: { ...cabeceras, "Content-Type": "application/pdf" },
  });
}
