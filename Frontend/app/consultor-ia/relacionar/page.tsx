"use client";

import { FormEvent, useEffect, useState } from "react";
import Pestanas from "../Pestanas";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";

type Convocatoria = {
  id: number;
  titulo: string | null;
  estado: string | null;
  fecha_cierre: string | null;
  descripcion: string | null;
};

type ConvocatoriasResponse = {
  items: Convocatoria[];
};

type Proyecto = {
  id: number;
  nombre: string | null;
  estado: string | null;
  anio: string | null;
  descripcion: string | null;
};

type Investigador = {
  id: number;
  nombre: string | null;
  apellido: string | null;
  institucion: string | null;
  titulo: string | null;
  investigaciones: string | null;
  nivel_sni: string | null;
  categoria_sni: string | null;
};

type Resultado = {
  key: string;
  tipo: "Convocatoria" | "Proyecto";
  titulo: string;
  descripcion: string;
  estado: string;
  detalle: string;
};

function texto(valor: string | null | undefined, vacio = "—") {
  const limpio = valor?.trim();
  return limpio ? limpio : vacio;
}

function formatFecha(valor: string | null) {
  if (!valor) return "Sin fecha";
  const [anio, mes, dia] = valor.slice(0, 10).split("-");
  if (!anio || !mes || !dia) return valor;
  return `${dia}/${mes}/${anio}`;
}

function nombreCompleto(persona: Investigador) {
  return texto([persona.nombre, persona.apellido].filter(Boolean).join(" "), "Sin nombre");
}

function sni(persona: Investigador) {
  const partes = [persona.nivel_sni, persona.categoria_sni]
    .map((parte) => parte?.trim())
    .filter(Boolean);
  return partes.length > 0 ? partes.join(" · ") : "—";
}

async function leerJson<T>(response: Response, recurso: string): Promise<T> {
  if (!response.ok) {
    throw new Error(`No se pudieron cargar ${recurso} (${response.status}).`);
  }
  return response.json() as Promise<T>;
}

export default function RelacionarPage() {
  const [borrador, setBorrador] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [resultados, setResultados] = useState<Resultado[]>([]);
  const [investigadores, setInvestigadores] = useState<Investigador[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controlador = new AbortController();

    async function cargar() {
      setCargando(true);
      setError(null);

      const consulta = busqueda.trim();
      const params = new URLSearchParams({ limit: "50" });
      if (consulta) params.set("buscar", consulta);
      const query = params.toString();

      try {
        const [convocatoriasRes, proyectosRes, investigadoresRes] = await Promise.all([
          fetch(`${API_URL}/api/convocatorias/?${query}`, { signal: controlador.signal }),
          fetch(`${API_URL}/api/proyectos/?${query}`, { signal: controlador.signal }),
          fetch(`${API_URL}/api/investigadores/?${query}`, { signal: controlador.signal }),
        ]);

        const [convocatorias, proyectos, personas] = await Promise.all([
          leerJson<ConvocatoriasResponse>(convocatoriasRes, "las convocatorias"),
          leerJson<Proyecto[]>(proyectosRes, "los proyectos"),
          leerJson<Investigador[]>(investigadoresRes, "los investigadores"),
        ]);

        const tarjetas: Resultado[] = [
          ...convocatorias.items.map((item) => ({
            key: `convocatoria-${item.id}`,
            tipo: "Convocatoria" as const,
            titulo: texto(item.titulo, "Sin título"),
            descripcion: texto(item.descripcion, "Sin descripción"),
            estado: texto(item.estado, "Sin estado"),
            detalle: `Cierre: ${formatFecha(item.fecha_cierre)}`,
          })),
          ...proyectos.map((item) => ({
            key: `proyecto-${item.id}`,
            tipo: "Proyecto" as const,
            titulo: texto(item.nombre, "Sin nombre"),
            descripcion: texto(item.descripcion, "Sin descripción"),
            estado: texto(item.estado, "Sin estado"),
            detalle: `Año: ${texto(item.anio)}`,
          })),
        ];

        setResultados(tarjetas);
        setInvestigadores(personas);
      } catch (err) {
        if (controlador.signal.aborted) return;
        setResultados([]);
        setInvestigadores([]);
        const mensaje = err instanceof Error ? err.message : "";
        setError(
          mensaje && mensaje !== "Failed to fetch"
            ? mensaje
            : "No se pudo conectar con el backend.",
        );
      } finally {
        if (!controlador.signal.aborted) setCargando(false);
      }
    }

    void cargar();

    return () => controlador.abort();
  }, [busqueda]);

  function enviar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusqueda(borrador);
  }

  return (
    <main>
      <section className="relative overflow-hidden px-6 pb-8 pt-12 sm:pt-16">
        <div className="blob pointer-events-none absolute -left-16 top-8 h-56 w-56 rounded-full bg-gold/50 blur-3xl" />
        <div className="blob-late pointer-events-none absolute right-0 top-16 h-64 w-64 rounded-full bg-pine/20 blur-3xl" />

        <div className="relative mx-auto max-w-6xl">
          <p className="rise text-sm font-medium tracking-[0.18em] text-clay uppercase">
            Consultor IA
          </p>
          <h1 className="rise rise-1 font-display mt-4 text-5xl leading-[1.05] text-ink sm:text-6xl">
            Relacionar
          </h1>
          <p className="rise rise-2 mt-6 max-w-2xl text-lg leading-relaxed text-ink/75">
            Contá de qué trata tu proyecto y encontrá fondos, antecedentes y personas afines.
          </p>
          <Pestanas actual="relacionar" />

          <form onSubmit={enviar} className="rise rise-3 mt-8">
            <label htmlFor="proyecto" className="mb-2 block text-sm text-ink">
              Contame de qué trata tu proyecto
            </label>
            <div className="relative">
              <textarea
                id="proyecto"
                name="proyecto"
                rows={5}
                value={borrador}
                onChange={(event) => setBorrador(event.target.value)}
                placeholder="Mi proyecto trata sobre..."
                className="w-full resize-none rounded-3xl border border-pine/20 bg-paper px-5 py-4 pr-16 text-sm text-ink shadow-sm outline-none transition focus:border-pine"
              />
              <button
                type="submit"
                className="absolute right-3 bottom-3 flex h-10 w-10 items-center justify-center rounded-full bg-pine text-ink transition hover:bg-pine-hover"
                aria-label="Buscar"
              >
                <Lupa />
              </button>
            </div>
          </form>

          {busqueda.trim() ? (
            <p className="rise mt-4 text-sm text-pine-text">
              Resultados para: {busqueda.trim()}
            </p>
          ) : null}
        </div>
      </section>

      <section className="px-6 pb-20">
        <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[1.6fr_0.9fr]">
          {error ? (
            <p className="rounded-2xl border border-clay/30 bg-paper px-5 py-4 text-sm text-ink lg:col-span-full" role="alert">
              {error} Comprobá que el backend esté disponible.
            </p>
          ) : null}

          {!error ? (
            <div className="flex flex-col gap-4">
              {cargando ? <Estado mensaje="Buscando fondos y antecedentes..." /> : null}
              {!cargando && resultados.length === 0 ? (
                <Estado mensaje="No hay convocatorias ni proyectos para esta búsqueda." />
              ) : null}
              {resultados.map((item, index) => (
                <article
                  key={item.key}
                  className={`rise rise-${(index % 4) + 1} rounded-3xl border border-pine/10 bg-paper p-5 shadow-sm transition duration-300 hover:-translate-y-1 hover:border-pine/30 hover:shadow-lg sm:p-6`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <p className="text-xs font-medium tracking-[0.16em] text-clay uppercase">{item.tipo}</p>
                    <p className="text-xs text-pine-text">{item.detalle}</p>
                  </div>
                  <h2 className="font-display mt-2 text-2xl text-ink">{item.titulo}</h2>
                  <p className="mt-3 text-sm leading-relaxed text-ink/70">{item.descripcion}</p>
                  <p className="mt-4 text-sm text-ink/80">
                    <span className="text-pine-text">Estado</span> · {item.estado}
                  </p>
                </article>
              ))}
            </div>
          ) : null}

          <aside className="rise rise-2 h-fit rounded-[2rem] bg-pine-deep px-6 py-8 text-paper">
            <h2 className="font-display text-3xl">Investigación</h2>
            <p className="mt-2 text-sm leading-relaxed text-paper/75">
              Personas e instituciones con trayectoria en el tema.
            </p>
            {cargando ? <p className="mt-6 text-sm text-paper/75">Cargando investigadores...</p> : null}
            {!cargando && error ? (
              <p className="mt-6 text-sm text-paper/75">No se pudieron cargar los investigadores.</p>
            ) : null}
            {!cargando && !error && investigadores.length === 0 ? (
              <p className="mt-6 text-sm text-paper/75">No hay investigadores para esta búsqueda.</p>
            ) : null}
            <ul className="mt-6 flex flex-col gap-4">
              {investigadores.map((persona) => (
                <li
                  key={persona.id}
                  className="rounded-2xl bg-white/10 p-4 ring-1 ring-white/15 transition duration-300 hover:bg-white/20"
                >
                  <p className="font-display text-xl">{nombreCompleto(persona)}</p>
                  <p className="mt-2 text-sm text-paper/80">{texto(persona.institucion, "Sin institución")}</p>
                  <p className="mt-1 text-sm text-paper/70">{texto(persona.titulo, "Sin título")}</p>
                  <p className="mt-3 text-sm leading-relaxed text-paper/75">
                    {texto(persona.investigaciones, "Sin investigaciones cargadas")}
                  </p>
                  <p className="mt-3 text-xs tracking-wide text-gold uppercase">SNI · {sni(persona)}</p>
                </li>
              ))}
            </ul>
          </aside>
        </div>
      </section>
    </main>
  );
}

function Estado({ mensaje }: { mensaje: string }) {
  return (
    <p className="rounded-3xl border border-dashed border-pine/30 bg-paper/70 px-6 py-10 text-center text-sm text-ink/70">
      {mensaje}
    </p>
  );
}

function Lupa() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <circle cx="7" cy="7" r="4.25" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M10.2 10.2 13 13" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
