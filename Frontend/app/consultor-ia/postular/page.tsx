"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import Loading from "../../components/Loading";
import FormularioCompletado from "../FormularioCompletado";
import type { CampoFormulario, Fuente } from "../formulario";
import Pestanas from "../Pestanas";
import Stepper from "../../components/Stepper";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";
const LIMITE_DOCUMENTOS = 3;
const PASOS = ["Formulario", "Documentos del proyecto", "Revisar y enviar"];

type RespuestaCampo = CampoFormulario;

type ResultadoJob = {
  job_id: number;
  estado: string;
  total_respuestas: number;
  validado: boolean;
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
  consultaToken: string | null,
  signal: AbortSignal,
  alConsultar: (estado: string) => void,
): Promise<ResultadoJob> {
  const limite = Date.now() + 45 * 60 * 1000;
  const maxFallosSeguidos = 24;
  let fallosSeguidos = 0;

  while (Date.now() < limite) {
    let response: Response;

    try {
      const consulta = consultaToken
        ? `?consulta=${encodeURIComponent(consultaToken)}`
        : "";
      response = await fetch(`${API_URL}/formularios/jobs/${jobId}/resultado${consulta}`, {
        signal,
        credentials: "include",
      });
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
      // 404 y 401 también se reintentan: el worker sigue y un rechazo aislado
      // no debe tirar abajo una carga que puede durar más que la sesión.
      if (response.status < 500 && response.status !== 404 && response.status !== 401) {
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
      dato_guardado: item.dato_guardado ?? null,
      tipo: item.tipo ?? null,
      pagina: item.pagina ?? null,
      fuentes: normalizarFuentes(item.fuentes),
    }));

    if (resultado.estado === "COMPLETED" || resultado.estado === "FAILED") {
      return {
        job_id: resultado.job_id,
        estado: resultado.estado,
        total_respuestas: resultado.total_respuestas,
        validado: Boolean(resultado.validado),
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
  const [validado, setValidado] = useState(false);
  const [paso, setPaso] = useState(0);
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
    const elegidos = Array.from(event.target.files ?? []);
    event.target.value = "";

    const siguientes = [...documentos];
    let superaElLimite = false;

    for (const archivo of elegidos) {
      const repetido = siguientes.some(
        (item) => item.name === archivo.name && item.size === archivo.size,
      );
      if (repetido) continue;
      if (siguientes.length >= LIMITE_DOCUMENTOS) {
        superaElLimite = true;
        break;
      }
      siguientes.push(archivo);
    }

    setDocumentos(siguientes);
    setErrorSubida(
      superaElLimite ? "Podés adjuntar hasta 3 documentos del proyecto." : null,
    );
  }

  function quitarDocumento(indice: number) {
    setDocumentos((actuales) => actuales.filter((_, posicion) => posicion !== indice));
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

    if (documentos.length > LIMITE_DOCUMENTOS) {
      setErrorSubida("Podés adjuntar hasta 3 documentos del proyecto.");
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

      const job = (await response.json()) as {
        id?: number;
        estado?: string;
        consulta_token?: string;
      };
      const idJob = job.id;
      if (typeof idJob !== "number" || !Number.isInteger(idJob)) {
        throw new Error("La API no devolvió el identificador del formulario.");
      }
      setEstadoJob(job.estado ?? "PENDING");
      setSubiendo(false);

      const resultado = await consultarResultado(
        idJob,
        job.consulta_token ?? null,
        controlador.signal,
        setEstadoJob,
      );

      if (resultado.estado === "FAILED") {
        throw new Error("El worker no pudo completar el formulario.");
      }

      setJobId(idJob);
      setValidado(resultado.validado);
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
    setValidado(false);
    setErrorSubida(null);
  }

  // Cada paso valida lo suyo antes de dejar avanzar
  function siguiente() {
    if (paso === 0 && !formulario) {
      setErrorSubida("Seleccioná el formulario de postulación.");
      return;
    }
    if (paso === 1 && documentos.length === 0) {
      setErrorSubida("Adjuntá al menos un documento del proyecto.");
      return;
    }
    setErrorSubida(null);
    setPaso((actual) => Math.min(actual + 1, PASOS.length - 1));
  }

  function anterior() {
    setErrorSubida(null);
    setPaso((actual) => Math.max(actual - 1, 0));
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

          <div className="relative mx-auto max-w-[100rem]">
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
          <div className="mx-auto max-w-[100rem]">
            <FormularioCompletado
              jobId={jobId}
              campos={respuestas}
              validado={validado}
              onVolver={volverAlFormulario}
            />
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

        <div className="relative mx-auto max-w-[100rem]">
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

          <div className="mt-8 rounded-3xl border-2 border-ink bg-paper p-5 shadow-sm sm:p-8">
            <Stepper pasos={PASOS} actual={paso} onIrA={setPaso} />

            <div className="mt-8 grid gap-4">
              {paso === 0 ? (
                <div>
                  <p className="mb-2 text-sm text-ink">Formulario de postulación</p>
                  <label
                    htmlFor="formulario-postulacion"
                    className="flex min-h-40 cursor-pointer flex-col items-center justify-center rounded-3xl border-2 border-dashed border-ink/70 bg-sand/60 px-6 py-8 text-center transition hover:border-pine hover:bg-paper"
                  >
                    <CloudUploadIcon />
                    <span className="mt-4 text-sm text-ink/70">
                      {formulario ? formulario.name : "Seleccionar formulario de postulación (PDF)"}
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
              ) : null}

              {paso === 1 ? (
                <>
                  <div>
                    <p className="mb-2 text-sm text-ink">
                      Documentación del proyecto
                      <span className="text-ink/55"> · hasta {LIMITE_DOCUMENTOS}</span>
                    </p>
                    <label
                      htmlFor="archivos-proyecto"
                      className="flex min-h-56 cursor-pointer flex-col items-center justify-center rounded-3xl border-2 border-dashed border-ink/70 bg-sand/60 px-6 py-10 text-center transition hover:border-pine hover:bg-paper"
                    >
                      <CloudUploadIcon />
                      <span className="mt-4 text-sm text-ink/70">
                        Elegí hasta 3 documentos. Podés seleccionar varios a la vez o añadirlos de a uno.
                      </span>
                      <input
                        id="archivos-proyecto"
                        name="documentos"
                        type="file"
                        multiple
                        accept=".pdf,.docx,.xlsx,.xls,.txt,.csv"
                        className="sr-only"
                        onChange={handleDocumentosChange}
                      />
                    </label>
                  </div>

                  <ListaDocumentos documentos={documentos} onQuitar={quitarDocumento} />
                </>
              ) : null}

              {paso === 2 ? (
                <div className="flex flex-col gap-4">
                  <div className="rounded-2xl border border-ink/20 bg-sand/60 px-5 py-4">
                    <p className="text-xs font-medium tracking-[0.16em] text-clay uppercase">Formulario</p>
                    <p className="mt-1 text-sm text-ink">{formulario?.name}</p>
                  </div>
                  <ListaDocumentos documentos={documentos} onQuitar={quitarDocumento} />
                  <p className="text-sm text-ink/70">
                    El consultor va a leer los documentos y completar el formulario. Después vas a poder revisar
                    cada campo, corregirlo y confirmar los datos.
                  </p>
                </div>
              ) : null}

              {errorSubida ? (
                <p className="rounded-2xl border border-clay/30 bg-paper px-5 py-4 text-sm text-ink" role="alert">
                  {errorSubida}
                </p>
              ) : null}

              <div className="flex items-center justify-between gap-3 border-t border-ink/15 pt-5">
                {paso > 0 ? (
                  <button
                    type="button"
                    onClick={anterior}
                    className="rounded-full border border-ink/30 bg-paper px-5 py-3 text-sm text-ink transition hover:border-pine hover:bg-foam"
                  >
                    Anterior
                  </button>
                ) : (
                  <span />
                )}
                {paso < PASOS.length - 1 ? (
                  <button
                    type="button"
                    onClick={siguiente}
                    className="rounded-full bg-pine px-5 py-3 text-sm font-medium text-ink shadow-sm transition duration-200 hover:-translate-y-0.5 hover:bg-pine-hover"
                  >
                    Siguiente
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handleSubir}
                    disabled={subiendo}
                    className="rounded-full bg-pine px-5 py-3 text-sm font-medium text-ink shadow-sm transition duration-200 hover:-translate-y-0.5 hover:bg-pine-hover disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
                  >
                    {subiendo ? "Subiendo..." : "Enviar al consultor"}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

function ListaDocumentos({
  documentos,
  onQuitar,
}: {
  documentos: File[];
  onQuitar: (indice: number) => void;
}) {
  if (documentos.length === 0) return null;

  return (
    <div className="rounded-3xl border border-ink/20 bg-paper p-5">
      <p className="text-sm text-pine-text">
        Documentos seleccionados ({documentos.length} de {LIMITE_DOCUMENTOS})
      </p>
      <ul className="mt-3 flex flex-col gap-2">
        {documentos.map((documento, index) => (
          <li
            key={`${documento.name}-${documento.size}-${index}`}
            className="flex items-center justify-between gap-3 rounded-2xl bg-sand px-4 py-2"
          >
            <span className="min-w-0 truncate text-sm text-ink/80">{documento.name}</span>
            <button
              type="button"
              onClick={() => onQuitar(index)}
              className="shrink-0 text-sm text-ink/50 transition hover:text-clay"
              aria-label={`Quitar ${documento.name}`}
            >
              Quitar
            </button>
          </li>
        ))}
      </ul>
    </div>
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
