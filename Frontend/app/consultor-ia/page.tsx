"use client";

import { FormEvent, useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
  icono: string;
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

export default function ConsultorIAPage() {
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
            icono: "📢",
            titulo: texto(item.titulo, "Sin título"),
            descripcion: texto(item.descripcion, "Sin descripción"),
            estado: texto(item.estado, "Sin estado"),
            detalle: `Cierre: ${formatFecha(item.fecha_cierre)}`,
          })),
          ...proyectos.map((item) => ({
            key: `proyecto-${item.id}`,
            tipo: "Proyecto" as const,
            icono: "📄",
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
        setError(
          err instanceof Error
            ? err.message
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
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-6 py-8">

      <div className="flex items-center gap-4">
        <div className="h-px flex-1 bg-black" />
        <h1 className="text-2xl font-normal text-black">
          Consultor IA
        </h1>
        <div className="h-px flex-1 bg-black" />
      </div>

      <p className="mt-3 text-center text-sm text-black">
        Buscar recursos relacionados a mi proyecto
      </p>

      <form className="mt-8" onSubmit={enviar}>
        <label htmlFor="proyecto" className="mb-2 block text-sm text-black">
          Cuentame de qué trata tu proyecto...
        </label>

        <div className="relative">
          <textarea
            id="proyecto"
            name="proyecto"
            rows={5}
            value={borrador}
            onChange={(event) => setBorrador(event.target.value)}
            placeholder="Mi proyecto trata sobre..."
            className="w-full resize-none border border-black bg-neutral-200 px-4 py-3 pr-12 text-sm outline-none"
          />
          <button
            type="submit"
            className="absolute right-3 top-3 flex h-8 w-8 items-center justify-center bg-neutral-700 text-white"
            aria-label="Buscar"
          >
            ✈
          </button>
        </div>
      </form>

      {busqueda.trim() ? (
        <p className="mt-4 text-sm text-black">
          Resultados para: {busqueda.trim()}
        </p>
      ) : null}

      {error ? (
        <p className="mt-6 border border-black bg-neutral-200 px-4 py-3 text-sm text-black">
          {error} Comprobá que el backend esté disponible en {API_URL}.
        </p>
      ) : null}

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-[2fr_1fr]">
        <div className="flex flex-col gap-4">
          {cargando ? (
            <p className="text-sm text-black">Cargando convocatorias y proyectos...</p>
          ) : null}

          {!cargando && !error && resultados.length === 0 ? (
            <p className="text-sm text-black">
              No hay convocatorias ni proyectos para esta búsqueda.
            </p>
          ) : null}

          {resultados.map((item) => (
            <article
              key={item.key}
              className="flex gap-4 bg-neutral-500 p-4 text-white"
            >
              <div className="flex h-12 w-12 shrink-0 items-center justify-center bg-neutral-700 text-2xl">
                {item.icono}
              </div>

              <div className="min-w-0 flex-1">
                <h2 className="text-base font-semibold">
                  “{item.titulo}”
                </h2>
                <p className="mt-2 text-xs leading-relaxed text-neutral-100">
                  <span className="font-semibold">Descripción:</span>{" "}
                  {item.descripcion}
                </p>
              </div>

              <div className="hidden shrink-0 text-right text-xs sm:block">
                <p>
                  <span className="font-semibold">Tipo:</span> {item.tipo}
                </p>
                <p className="mt-1">
                  <span className="font-semibold">Estado:</span> {item.estado}
                </p>
                <p className="mt-1">{item.detalle}</p>
              </div>
            </article>
          ))}
        </div>

        <aside className="bg-neutral-500 p-4 text-white">
          {cargando ? (
            <p className="text-xs">Cargando investigadores...</p>
          ) : null}

          {!cargando && !error && investigadores.length === 0 ? (
            <p className="text-xs">No hay investigadores para esta búsqueda.</p>
          ) : null}

          <div className="flex flex-col gap-5">
            {investigadores.map((persona) => (
              <div key={persona.id} className="flex gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-neutral-700 text-lg">
                  👤
                </div>
                <div className="text-xs leading-relaxed">
                  <p className="text-sm font-semibold">{nombreCompleto(persona)}</p>
                  <p>
                    <span className="font-semibold">Institución:</span>{" "}
                    {texto(persona.institucion)}
                  </p>
                  <p>
                    <span className="font-semibold">Título:</span>{" "}
                    {texto(persona.titulo)}
                  </p>
                  <p>
                    <span className="font-semibold">Investigaciones:</span>{" "}
                    {texto(persona.investigaciones)}
                  </p>
                  <p>
                    <span className="font-semibold">SNI:</span> {sni(persona)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </aside>
      </div>

      <section className="mt-16">
        <div className="flex items-center gap-4">
          <div className="h-px flex-1 bg-black" />
          <h2 className="text-2xl font-normal text-black">
            Consultor IA
          </h2>
          <div className="h-px flex-1 bg-black" />
        </div>

        <p className="mt-3 text-center text-sm text-black">
          Completar un formulario de postulación
        </p>

        <div className="mx-auto mt-10 max-w-5xl">
          <p className="mb-3 text-sm text-black">
            Adjunta documentación sobre tu Proyecto...
          </p>

          <label
            htmlFor="archivos-proyecto"
            className="flex min-h-64 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-sky-500 bg-white px-6 py-10 text-center"
          >
            <CloudUploadIcon />
            <span className="mt-4 text-sm text-neutral-700">
              Puede arrastrar y soltar archivos aquí para añadirlos
            </span>
            <input
              id="archivos-proyecto"
              name="archivos"
              type="file"
              multiple
              className="sr-only"
            />
          </label>

          <div className="mt-4 flex justify-end">
            <button
              type="button"
              className="border border-black bg-neutral-300 px-8 py-2 text-sm text-black"
            >
              Subir
            </button>
          </div>
        </div>
      </section>

    </main>
  );
}

function CloudUploadIcon() {
  return (
    <svg
      width="72"
      height="72"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className="text-black"
      aria-hidden="true"
    >
      <path d="M7 18a4.5 4.5 0 0 1 .4-9 5.5 5.5 0 0 1 10.7 1.5A3.5 3.5 0 0 1 17.5 18H7z" />
      <path d="M12 15V9" />
      <path d="M9.5 11.5 12 9l2.5 2.5" />
    </svg>
  );
}
