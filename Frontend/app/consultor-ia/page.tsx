"use client";

import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import Loading from "../components/Loading";
import FormularioCompletado from "./FormularioCompletado";
import type { CampoFormulario, Fuente } from "./formulario";

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

type RespuestaCampo = CampoFormulario;

type ResultadoJob = {
  job_id: number;
  estado: string;
  total_respuestas: number;
  respuestas: RespuestaCampo[];
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

function normalizarFuentes(valor: unknown): Fuente[] {
  let fuentes = valor;

  if (typeof fuentes === "string") {
    try {
      fuentes = JSON.parse(fuentes) as unknown;
    } catch {
      return [];
    }
  }

  if (!Array.isArray(fuentes)) return [];

  return fuentes.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const fuente = item as { pagina?: unknown; archivo?: unknown };
    if (typeof fuente.archivo !== "string" || !fuente.archivo.trim()) return [];
    return [
      {
        pagina: typeof fuente.pagina === "number" ? fuente.pagina : null,
        archivo: fuente.archivo,
      },
    ];
  });
}

function esperar(ms: number, signal: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }

    const id = window.setTimeout(() => resolve(), ms);
    signal.addEventListener(
      "abort",
      () => {
        window.clearTimeout(id);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}

function mensajeEstado(estado: string | null) {
  if (estado === "PROCESSING") return "Procesando los documentos del proyecto.";
  if (estado === "PENDING") return "El formulario está en cola.";
  return "Subiendo los documentos.";
}

async function consultarResultado(
  jobId: number,
  signal: AbortSignal,
  alConsultar: (estado: string) => void,
): Promise<ResultadoJob> {
  // Qwen corre en CPU: un formulario puede tardar más de 20 minutos
  const limite = Date.now() + 45 * 60 * 1000;
  // Tolera cortes breves (p. ej. un 502 mientras el túnel de Cloudflare se reconecta)
  const maxFallosSeguidos = 24;
  let fallosSeguidos = 0;

  while (Date.now() < limite) {
    let response: Response;

    try {
      response = await fetch(`${API_URL}/formularios/jobs/${jobId}/resultado`, { signal });
    } catch (error) {
      if (signal.aborted) throw error;
      fallosSeguidos += 1;
      if (fallosSeguidos >= maxFallosSeguidos) {
        throw new Error("No se pudo conectar con el servidor para consultar el resultado.");
      }
      await esperar(5000, signal);
      continue;
    }

    if (!response.ok) {
      if (response.status < 500) {
        throw new Error(`No se pudo consultar el resultado (${response.status}).`);
      }
      fallosSeguidos += 1;
      if (fallosSeguidos >= maxFallosSeguidos) {
        throw new Error(`No se pudo consultar el resultado (${response.status}).`);
      }
      await esperar(5000, signal);
      continue;
    }

    fallosSeguidos = 0;

    const resultado = (await response.json()) as Omit<ResultadoJob, "respuestas"> & {
      respuestas?: Array<Omit<RespuestaCampo, "fuentes"> & { fuentes: unknown }>;
    };

    alConsultar(resultado.estado);

    const respuestas = (resultado.respuestas ?? []).map((item) => ({
      ...item,
      respuesta_ia: item.respuesta_ia ?? null,
      editada: Boolean(item.editada),
      tipo: item.tipo ?? null,
      pagina: item.pagina ?? null,
      fuentes: normalizarFuentes(item.fuentes),
    }));

    if (resultado.estado === "COMPLETED" || resultado.estado === "FAILED") {
      return {
        job_id: resultado.job_id,
        estado: resultado.estado,
        total_respuestas: resultado.total_respuestas,
        respuestas,
      };
    }

    await esperar(5000, signal);
  }

  throw new Error("El worker tardó demasiado en completar el formulario.");
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
  const [formulario, setFormulario] = useState<File | null>(null);
  const [documentos, setDocumentos] = useState<File[]>([]);
  const [subiendo, setSubiendo] = useState(false);
  const [vista, setVista] = useState<"consultor" | "cargando" | "resultado">("consultor");
  const [estadoJob, setEstadoJob] = useState<string | null>(null);
  const [respuestas, setRespuestas] = useState<RespuestaCampo[]>([]);
  const [jobId, setJobId] = useState<number | null>(null);
  const [errorSubida, setErrorSubida] = useState<string | null>(null);
  const consultaJob = useRef<AbortController | null>(null);

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

  useEffect(() => {
    return () => consultaJob.current?.abort();
  }, []);

  function enviar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusqueda(borrador);
  }

  function handleFormularioChange(event: ChangeEvent<HTMLInputElement>) {
    setFormulario(event.target.files?.[0] ?? null);
    setErrorSubida(null);
  }

  function handleDocumentosChange(event: ChangeEvent<HTMLInputElement>) {
    setDocumentos(Array.from(event.target.files ?? []));
    setErrorSubida(null);
  }

  async function handleSubir() {
    if (!formulario) {
      setErrorSubida("Seleccioná el formulario de postulación.");
      return;
    }

    if (documentos.length === 0) {
      setErrorSubida("Adjuntá al menos un documento del proyecto.");
      return;
    }

    const cuerpo = new FormData();
    cuerpo.append("formulario", formulario);
    for (const documento of documentos) {
      cuerpo.append("documentos", documento);
    }

    consultaJob.current?.abort();
    const controlador = new AbortController();
    consultaJob.current = controlador;

    setSubiendo(true);
    setVista("cargando");
    setEstadoJob(null);
    setErrorSubida(null);
    setRespuestas([]);

    try {
      const response = await fetch(`${API_URL}/formularios/jobs`, {
        method: "POST",
        body: cuerpo,
        signal: controlador.signal,
      });

      if (!response.ok) {
        throw new Error(`No se pudo crear el job (${response.status}).`);
      }

      const job = (await response.json()) as { id: number; estado?: string };
      setEstadoJob(job.estado ?? "PENDING");
      setSubiendo(false);

      const resultado = await consultarResultado(job.id, controlador.signal, setEstadoJob);

      if (resultado.estado === "FAILED") {
        throw new Error("El worker no pudo completar el formulario.");
      }

      setJobId(job.id);
      setRespuestas(resultado.respuestas);
      setVista("resultado");
    } catch (err) {
      if (controlador.signal.aborted) return;
      setVista("consultor");
      setErrorSubida(
        err instanceof Error ? err.message : "No se pudieron subir los archivos.",
      );
    } finally {
      if (!controlador.signal.aborted) {
        setSubiendo(false);
      }
    }
  }

  function volverAlConsultor() {
    setVista("consultor");
    setEstadoJob(null);
    setRespuestas([]);
    setJobId(null);
    setErrorSubida(null);
  }

  if (vista === "cargando") {
    return <Loading mensaje={mensajeEstado(estadoJob)} />;
  }

  if (vista === "resultado" && jobId != null) {
    return (
      <main>
        <section className="relative overflow-hidden px-6 pb-8 pt-12 sm:pt-16">
          <div className="blob pointer-events-none absolute -left-16 top-8 h-56 w-56 rounded-full bg-gold/50 blur-3xl" />
          <div className="blob-late pointer-events-none absolute right-0 top-16 h-64 w-64 rounded-full bg-pine/20 blur-3xl" />

          <div className="relative mx-auto max-w-6xl">
            <p className="rise text-sm font-medium tracking-[0.18em] text-clay uppercase">
              Relacionar · Uruguay
            </p>
            <h1 className="rise rise-1 font-display mt-4 text-5xl leading-[1.05] text-ink sm:text-6xl">
              Formulario completado
            </h1>
            <p className="rise rise-2 mt-6 max-w-2xl text-lg leading-relaxed text-ink/75">
              El consultor llenó el formulario con lo que encontró en los documentos del proyecto.
              Revisalo, corregí lo que haga falta y descargalo en PDF.
            </p>
          </div>
        </section>

        <section className="px-6 pb-20">
          <div className="mx-auto max-w-4xl">
            <FormularioCompletado jobId={jobId} campos={respuestas} onVolver={volverAlConsultor} />
          </div>
        </section>
      </main>
    );
  }

  return (
    <main>
      <section className="relative overflow-hidden px-6 pb-8 pt-12 sm:pt-16">
        <div className="blob pointer-events-none absolute -left-16 top-8 h-56 w-56 rounded-full bg-gold/50 blur-3xl" />
        <div className="blob-late pointer-events-none absolute right-0 top-16 h-64 w-64 rounded-full bg-pine/20 blur-3xl" />

        <div className="relative mx-auto max-w-6xl">
          <p className="rise text-sm font-medium tracking-[0.18em] text-clay uppercase">
            Relacionar · Uruguay
          </p>
          <h1 className="rise rise-1 font-display mt-4 text-5xl leading-[1.05] text-ink sm:text-6xl">
            Consultor IA
          </h1>
          <p className="rise rise-2 mt-6 max-w-2xl text-lg leading-relaxed text-ink/75">
            Contá de qué trata tu proyecto y encontrá fondos, antecedentes y personas afines.
          </p>

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

      <section className="px-6 pb-8">
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

      <section className="px-6 pb-20">
        <div className="mx-auto max-w-6xl">
          <p className="text-sm font-medium tracking-[0.18em] text-clay uppercase">Postular</p>
          <h2 className="font-display mt-3 text-4xl text-ink">Completar un formulario</h2>
          <p className="mt-3 max-w-2xl text-ink/75">
            Subí la postulación y los documentos del proyecto para que el consultor los lea.
          </p>

          <div className="mt-8 grid gap-4">
            <div>
              <p className="mb-2 text-sm text-ink">Formulario de postulación</p>
              <label
                htmlFor="formulario-postulacion"
                className="flex min-h-32 cursor-pointer flex-col items-center justify-center rounded-3xl border border-dashed border-pine/30 bg-paper/70 px-6 py-8 text-center transition hover:border-pine hover:bg-paper"
              >
                <span className="text-sm text-ink/70">
                  {formulario ? formulario.name : "Seleccionar formulario de postulación"}
                </span>
                <input
                  id="formulario-postulacion"
                  type="file"
                  accept=".pdf"
                  className="sr-only"
                  onChange={handleFormularioChange}
                />
              </label>
            </div>

            <div>
              <p className="mb-2 text-sm text-ink">Documentación del proyecto</p>
              <label
                htmlFor="archivos-proyecto"
                className="flex min-h-56 cursor-pointer flex-col items-center justify-center rounded-3xl border border-dashed border-pine/30 bg-paper/70 px-6 py-10 text-center transition hover:border-pine hover:bg-paper"
              >
                <CloudUploadIcon />
                <span className="mt-4 text-sm text-ink/70">
                  Arrastrá y soltá archivos aquí, o hacé clic para añadirlos
                </span>
                <input
                  id="archivos-proyecto"
                  name="documentos"
                  type="file"
                  multiple
                  className="sr-only"
                  onChange={handleDocumentosChange}
                />
              </label>
            </div>

            {documentos.length > 0 ? (
              <div className="rounded-3xl border border-pine/10 bg-paper p-5 shadow-sm">
                <p className="text-sm text-pine-text">Documentos seleccionados</p>
                <ul className="mt-3 flex flex-col gap-1">
                  {documentos.map((documento, index) => (
                    <li key={`${documento.name}-${index}`} className="text-sm text-ink/80">
                      {documento.name}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {errorSubida ? (
              <p className="rounded-2xl border border-clay/30 bg-paper px-5 py-4 text-sm text-ink" role="alert">
                {errorSubida}
              </p>
            ) : null}

            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleSubir}
                disabled={subiendo}
                className="rounded-full bg-pine px-5 py-3 text-sm font-medium text-ink shadow-sm transition duration-200 hover:-translate-y-0.5 hover:bg-pine-hover disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
              >
                {subiendo ? "Subiendo..." : "Subir"}
              </button>
            </div>
          </div>
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

function CloudUploadIcon() {
  return (
    <svg
      width="72"
      height="72"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      className="text-pine"
      aria-hidden="true"
    >
      <path d="M7 18a4.5 4.5 0 0 1 .4-9 5.5 5.5 0 0 1 10.7 1.5A3.5 3.5 0 0 1 17.5 18H7z" />
      <path d="M12 15V9" />
      <path d="M9.5 11.5 12 9l2.5 2.5" />
    </svg>
  );
}
