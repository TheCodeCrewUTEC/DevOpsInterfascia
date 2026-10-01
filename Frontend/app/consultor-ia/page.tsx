"use client";

import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import Loading from "../components/Loading";

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

type Fuente = {
  pagina: number | null;
  archivo: string;
};

type RespuestaCampo = {
  campo: string;
  respuesta: string | null;
  fuentes: Fuente[];
};

type ResultadoJob = {
  job_id: number;
  estado: string;
  total_respuestas: number;
  respuestas: RespuestaCampo[];
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
  const limite = Date.now() + 10 * 60 * 1000;

  while (Date.now() < limite) {
    const response = await fetch(`${API_URL}/formularios/jobs/${jobId}/resultado`, { signal });

    if (!response.ok) {
      throw new Error(`No se pudo consultar el resultado (${response.status}).`);
    }

    const resultado = (await response.json()) as Omit<ResultadoJob, "respuestas"> & {
      respuestas?: Array<Omit<RespuestaCampo, "fuentes"> & { fuentes: unknown }>;
    };

    alConsultar(resultado.estado);

    const respuestas = (resultado.respuestas ?? []).map((item) => ({
      campo: item.campo,
      respuesta: item.respuesta,
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
    setErrorSubida(null);
  }

  if (vista === "cargando") {
    return <Loading mensaje={mensajeEstado(estadoJob)} />;
  }

  if (vista === "resultado") {
    return (
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-6 py-8">
        <div className="flex items-center gap-4">
          <div className="h-px flex-1 bg-black" />
          <h1 className="text-2xl font-normal text-black">Consultor IA</h1>
          <div className="h-px flex-1 bg-black" />
        </div>
        <p className="mt-3 text-center text-sm text-black">
          Respuestas del formulario
        </p>
        <div className="mx-auto mt-10 flex w-full max-w-5xl flex-col gap-4">
          {respuestas.length === 0 ? (
            <p className="rounded-lg border border-neutral-300 bg-white p-4 text-sm text-neutral-800">
              El formulario se completó sin respuestas.
            </p>
          ) : (
            respuestas.map((item, index) => (
              <article
                key={`${item.campo}-${index}`}
                className="rounded-lg border border-neutral-300 bg-white p-4"
              >
                <p className="text-sm font-medium text-black">{item.campo}</p>
                <p className="mt-2 text-sm text-neutral-800">
                  {item.respuesta?.trim()
                    ? item.respuesta
                    : "Sin información en los documentos"}
                </p>
                {item.fuentes.length > 0 ? (
                  <ul className="mt-3 space-y-1">
                    {item.fuentes.map((fuente, fuenteIndex) => (
                      <li
                        key={`${fuente.archivo}-${fuente.pagina ?? "s"}-${fuenteIndex}`}
                        className="text-xs text-neutral-600"
                      >
                        {fuente.archivo}
                        {fuente.pagina != null ? ` · página ${fuente.pagina}` : ""}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </article>
            ))
          )}
          <div className="mt-4 flex justify-end">
            <button
              type="button"
              onClick={volverAlConsultor}
              className="border border-black bg-neutral-300 px-8 py-2 text-sm text-black"
            >
              Volver
            </button>
          </div>
        </div>
      </main>
    );
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

        {/* FORMULARIO DE POSTULACIÓN */}

        <p className="mb-3 text-sm text-black">
          Selecciona el formulario de postulación
        </p>

        <label
          htmlFor="formulario-postulacion"
          className="flex min-h-32 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-sky-500 bg-white px-6 py-8 text-center"
        >
          <span className="text-sm text-neutral-700">
            {formulario
              ? formulario.name
              : "Seleccionar formulario de postulación"}
          </span>

          <input
            id="formulario-postulacion"
            type="file"
            accept=".pdf"
            className="sr-only"
            onChange={handleFormularioChange}
          />
        </label>


        {/* DOCUMENTOS DEL PROYECTO */}

        <p className="mb-3 mt-8 text-sm text-black">
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
              name="documentos"
              type="file"
              multiple
              className="sr-only"
              onChange={handleDocumentosChange}
            />
          </label>

          {documentos.length > 0 && (
          <div className="mt-4 rounded-lg border border-neutral-300 bg-white p-4">

            <p className="mb-2 text-sm font-medium text-black">
              Documentos seleccionados:
            </p>

            <ul className="space-y-1">
              {documentos.map((documento, index) => (
                <li
                  key={`${documento.name}-${index}`}
                  className="text-sm text-neutral-700"
                >
                  {documento.name}
                </li>
              ))}
            </ul>

          </div>
        )}
        {errorSubida && (
          <div className="mt-4 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700">
            {errorSubida}
          </div>
        )}

          <div className="mt-4 flex justify-end">
            <button
              type="button"
              onClick={handleSubir}
              disabled={subiendo}
              className="border border-black bg-neutral-300 px-8 py-2 text-sm text-black disabled:cursor-not-allowed disabled:opacity-50"
            >
              {subiendo ? "Subiendo..." : "Subir"}
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
