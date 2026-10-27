import type { Metadata } from "next";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import {
  ETIQUETAS_VISTA,
  VISTAS,
  hrefAnalisis,
  leerFiltros,
  queryDeFiltros,
  type AnalisisFondos,
  type AnalisisInvestigadores,
  type AnalisisProyectos,
  type AnalisisTendencias,
  type OpcionesAnalisis,
  type ResumenAnalisis,
} from "@/lib/analisis";
import BotonesExportar from "./BotonesExportar";
import FiltrosAnaliticos from "./FiltrosAnaliticos";
import VistaFondos from "./VistaFondos";
import VistaInvestigadores from "./VistaInvestigadores";
import VistaProyectos from "./VistaProyectos";
import VistaResumen from "./VistaResumen";
import VistaTendencias from "./VistaTendencias";
import "./graficos.css";

export const metadata: Metadata = {
  title: "Análisis de Datos | Interfascia",
};

export const dynamic = "force-dynamic";

// Pide un endpoint de /api/analisis; si falla devuelve el detail de la API para mostrarlo
async function obtener<T>(path: string): Promise<{ datos: T | null; error: string | null }> {
  try {
    const response = await apiFetch(path, { cache: "no-store" });
    if (response.ok) {
      return { datos: (await response.json()) as T, error: null };
    }
    const cuerpo = await response.json().catch(() => null);
    const detalle = typeof cuerpo?.detail === "string" ? cuerpo.detail : null;
    return { datos: null, error: detalle ?? `No se pudieron cargar los datos (${response.status}).` };
  } catch {
    return { datos: null, error: "No se pudo conectar con la API." };
  }
}

export default async function AnalisisDatosPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const filtros = leerFiltros(await searchParams);
  const query = queryDeFiltros(filtros, filtros.vista === "tendencias" ? { agrupar: filtros.agrupar } : {});

  const [opciones, vista] = await Promise.all([
    obtener<OpcionesAnalisis>("/api/analisis/opciones"),
    obtener<unknown>(`/api/analisis/${filtros.vista}${query ? `?${query}` : ""}`),
  ]);

  const hrefExportar = (formato: "csv" | "pdf") =>
    `/analisis-datos/exportar?${queryDeFiltros(filtros, {
      formato,
      vista: filtros.vista,
      agrupar: filtros.vista === "tendencias" ? filtros.agrupar : undefined,
    })}`;

  return (
    <main className="mx-auto flex w-full max-w-[100rem] flex-1 flex-col gap-6 px-6 py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium tracking-[0.18em] text-clay uppercase">Plataforma</p>
          <h1 className="font-display mt-2 text-4xl text-balance text-ink">Análisis de Datos</h1>
          <p className="mt-2 text-sm text-ink/70">
            Indicadores y distribución de fondos, investigadores y proyectos cargados en Interfascia.
          </p>
        </div>
        {/* Exportación de la vista activa con los filtros aplicados (RF006-07) */}
        <div data-acciones="exportar">
          <BotonesExportar
            hrefs={{
              csv: hrefExportar("csv"),
              pdf: hrefExportar("pdf"),
            }}
          />
        </div>
      </div>

      <nav className="flex flex-wrap gap-2" aria-label="Secciones del análisis">
        {VISTAS.map((valor) => (
          <Link
            key={valor}
            href={hrefAnalisis(filtros, { vista: valor })}
            aria-current={valor === filtros.vista ? "page" : undefined}
            className={
              valor === filtros.vista
                ? "presionable inline-flex min-h-10 items-center rounded-full border-2 border-ink bg-pine px-4 text-sm text-ink pointer-coarse:min-h-11"
                : "presionable inline-flex min-h-10 items-center rounded-full border-2 border-ink bg-paper px-4 text-sm text-ink hover:bg-foam pointer-coarse:min-h-11"
            }
          >
            {ETIQUETAS_VISTA[valor]}
          </Link>
        ))}
      </nav>

      {/* key: al cambiar los filtros de la URL el formulario se vuelve a montar con esos valores */}
      <FiltrosAnaliticos key={queryDeFiltros(filtros)} filtros={filtros} opciones={opciones.datos} />

      {opciones.error ? <AvisoError texto={`No se pudieron cargar las opciones de filtro: ${opciones.error}`} /> : null}
      {vista.error ? <AvisoError texto={vista.error} /> : null}

      {vista.datos ? (
        <section aria-label={ETIQUETAS_VISTA[filtros.vista]}>
          {filtros.vista === "resumen" ? <VistaResumen datos={vista.datos as ResumenAnalisis} filtros={filtros} /> : null}
          {filtros.vista === "fondos" ? <VistaFondos datos={vista.datos as AnalisisFondos} filtros={filtros} /> : null}
          {filtros.vista === "investigadores" ? (
            <VistaInvestigadores datos={vista.datos as AnalisisInvestigadores} filtros={filtros} />
          ) : null}
          {filtros.vista === "proyectos" ? <VistaProyectos datos={vista.datos as AnalisisProyectos} filtros={filtros} /> : null}
          {filtros.vista === "tendencias" ? (
            <VistaTendencias datos={vista.datos as AnalisisTendencias} filtros={filtros} />
          ) : null}
        </section>
      ) : null}
    </main>
  );
}

function AvisoError({ texto }: { texto: string }) {
  return (
    <p role="alert" className="rounded-2xl border border-clay/30 bg-clay/10 px-4 py-3 text-sm text-ink">
      {texto}
    </p>
  );
}
