"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import Loading from "../../components/Loading";
import FormularioCompletado from "../FormularioCompletado";
import type { CampoFormulario, Fuente } from "../formulario";
import Pestanas from "../Pestanas";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";

type RespuestaCampo = CampoFormulario;

type ResultadoJob = {
  job_id: number;
  estado: string;
  total_respuestas: number;
  respuestas: RespuestaCampo[];
};

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
  const limite = Date.now() + 45 * 60 * 1000;
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

export default function PostularPage() {
  const [formulario, setFormulario] = useState<File | null>(null);
  const [documentos, setDocumentos] = useState<File[]>([]);
  const [subiendo, setSubiendo] = useState(false);
  const [vista, setVista] = useState<"formulario" | "cargando" | "resultado">("formulario");
  const [estadoJob, setEstadoJob] = useState<string | null>(null);
  const [respuestas, setRespuestas] = useState<RespuestaCampo[]>([]);
  const [jobId, setJobId] = useState<number | null>(null);
  const [errorSubida, setErrorSubida] = useState<string | null>(null);
  const consultaJob = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => consultaJob.current?.abort();
  }, []);

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

      const job = (await response.json()) as { id?: number; estado?: string };
      const idJob = job.id;
      if (typeof idJob !== "number" || !Number.isInteger(idJob)) {
        throw new Error("La API no devolvió el identificador del formulario.");
      }
      setEstadoJob(job.estado ?? "PENDING");
      setSubiendo(false);

      const resultado = await consultarResultado(idJob, controlador.signal, setEstadoJob);

      if (resultado.estado === "FAILED") {
        throw new Error("El worker no pudo completar el formulario.");
      }

      setJobId(idJob);
      setRespuestas(resultado.respuestas);
      setVista("resultado");
    } catch (err) {
      if (controlador.signal.aborted) return;
      setVista("formulario");
      setErrorSubida(
        err instanceof Error ? err.message : "No se pudieron subir los archivos.",
      );
    } finally {
      if (!controlador.signal.aborted) {
        setSubiendo(false);
      }
    }
  }

  function volverAlFormulario() {
    setVista("formulario");
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
              Consultor IA · Postular
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
            <FormularioCompletado jobId={jobId} campos={respuestas} onVolver={volverAlFormulario} />
          </div>
        </section>
      </main>
    );
  }

  return (
    <main>
      <section className="relative overflow-hidden px-6 pb-20 pt-12 sm:pt-16">
        <div className="blob pointer-events-none absolute -left-16 top-8 h-56 w-56 rounded-full bg-gold/50 blur-3xl" />
        <div className="blob-late pointer-events-none absolute right-0 top-16 h-64 w-64 rounded-full bg-pine/20 blur-3xl" />

        <div className="relative mx-auto max-w-6xl">
          <p className="rise text-sm font-medium tracking-[0.18em] text-clay uppercase">
            Consultor IA
          </p>
          <h1 className="rise rise-1 font-display mt-4 text-5xl leading-[1.05] text-ink sm:text-6xl">
            Postular
          </h1>
          <p className="rise rise-2 mt-6 max-w-2xl text-lg leading-relaxed text-ink/75">
            Subí la postulación y los documentos del proyecto para que el consultor los lea.
          </p>
          <Pestanas actual="postular" />

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
