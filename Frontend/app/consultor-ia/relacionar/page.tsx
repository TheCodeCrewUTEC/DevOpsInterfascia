"use client";

import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";
import Pestanas from "../Pestanas";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";
const LIMITE_DOCUMENTOS = 3;
const CLAVE = "relacionar-conversacion";

const SUGERENCIAS = [
  "¿Qué fondos de financiamiento se adecuan más a mi proyecto?",
  "¿Qué requisitos piden esos fondos?",
  "¿Cómo es el proceso de postulación?",
];

type Fondo = {
  id: number;
  titulo: string | null;
  estado: string | null;
  motivo?: string | null;
};

type Mensaje = {
  rol: string;
  contenido: string;
  fondos?: Fondo[];
};

type Conversacion = {
  id: number;
  estado: string;
  error: string | null;
  documentos: string[];
  mensajes: Mensaje[];
};

async function leerError(response: Response, respaldo: string) {
  const data = await response.json().catch(() => null);
  const detail = data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail) && typeof detail[0]?.msg === "string") return detail[0].msg;
  return `${respaldo} (${response.status}).`;
}

export default function RelacionarPage() {
  const [documentos, setDocumentos] = useState<File[]>([]);
  const [conversacion, setConversacion] = useState<Conversacion | null>(null);
  const [fase, setFase] = useState<"cargando" | "subir" | "chat">("cargando");
  const [subiendo, setSubiendo] = useState(false);
  const [pregunta, setPregunta] = useState("");
  const [pensando, setPensando] = useState(false);
  const [error, setError] = useState("");
  const hilo = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const guardada = sessionStorage.getItem(CLAVE);
    if (!guardada || guardada === "nueva") {
      setFase("subir");
      return;
    }
    const id = Number(guardada);
    if (!Number.isInteger(id)) {
      sessionStorage.setItem(CLAVE, "nueva");
      setFase("subir");
      return;
    }

    let activa = true;
    fetch(`${API_URL}/api/relacionar/conversaciones/${id}`)
      .then(async (response) => {
        if (!activa || sessionStorage.getItem(CLAVE) !== guardada) return;
        if (!response.ok) {
          sessionStorage.setItem(CLAVE, "nueva");
          setFase("subir");
          return;
        }
        const data = (await response.json()) as Conversacion;
        if (!activa || sessionStorage.getItem(CLAVE) !== guardada) return;
        setConversacion(data);
        setFase("chat");
      })
      .catch(() => {
        if (!activa || sessionStorage.getItem(CLAVE) !== guardada) return;
        sessionStorage.setItem(CLAVE, "nueva");
        setFase("subir");
      });

    return () => {
      activa = false;
    };
  }, []);

  useEffect(() => {
    if (!conversacion) return;
    if (conversacion.estado !== "PENDING" && conversacion.estado !== "PROCESSING") return;

    const id = conversacion.id;
    const timer = setInterval(async () => {
      try {
        const response = await fetch(`${API_URL}/api/relacionar/conversaciones/${id}`);
        if (!response.ok || sessionStorage.getItem(CLAVE) !== String(id)) return;
        const data = (await response.json()) as Conversacion;
        if (sessionStorage.getItem(CLAVE) !== String(id)) return;
        setConversacion(data);
      } catch {
        // El próximo intento vuelve a consultar.
      }
    }, 4000);

    return () => clearInterval(timer);
  }, [conversacion]);

  useEffect(() => {
    hilo.current?.scrollTo({ top: hilo.current.scrollHeight });
  }, [conversacion?.mensajes.length, pensando]);

  function elegirDocumentos(lista: File[]) {
    if (lista.length === 0) return;
    setError("");
    setDocumentos((actuales) => {
      const siguientes = [...actuales];
      for (const archivo of lista) {
        if (siguientes.length >= LIMITE_DOCUMENTOS) break;
        const repetido = siguientes.some(
          (documento) => documento.name === archivo.name && documento.size === archivo.size,
        );
        if (!repetido) siguientes.push(archivo);
      }
      return siguientes;
    });
  }

  async function subir() {
    if (documentos.length === 0 || subiendo) return;
    setSubiendo(true);
    setError("");
    try {
      const cuerpo = new FormData();
      documentos.forEach((documento) => cuerpo.append("documentos", documento));
      const response = await fetch(`${API_URL}/api/relacionar/conversaciones`, {
        method: "POST",
        body: cuerpo,
      });
      if (!response.ok) {
        throw new Error(await leerError(response, "No se pudieron subir los documentos"));
      }
      const data = (await response.json()) as Conversacion;
      sessionStorage.setItem(CLAVE, String(data.id));
      setConversacion(data);
      setFase("chat");
      setDocumentos([]);
    } catch (err) {
      const mensaje = err instanceof Error ? err.message : "";
      setError(mensaje && mensaje !== "Failed to fetch" ? mensaje : "No se pudo conectar con el backend.");
    } finally {
      setSubiendo(false);
    }
  }

  async function enviar(texto: string) {
    const limpio = texto.trim();
    if (!conversacion || !limpio || pensando) return;
    setPensando(true);
    setError("");
    setPregunta("");
    setConversacion({
      ...conversacion,
      mensajes: [...conversacion.mensajes, { rol: "usuario", contenido: limpio }],
    });
    try {
      const response = await fetch(
        `${API_URL}/api/relacionar/conversaciones/${conversacion.id}/mensajes`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ texto: limpio }),
        },
      );
      if (!response.ok) {
        throw new Error(await leerError(response, "No se pudo consultar a Qwen"));
      }
      const data = (await response.json()) as { contenido: string; fondos: Fondo[] };
      setConversacion((actual) =>
        actual
          ? {
              ...actual,
              mensajes: [
                ...actual.mensajes,
                { rol: "asistente", contenido: data.contenido, fondos: data.fondos ?? [] },
              ],
            }
          : actual,
      );
    } catch (err) {
      const mensaje = err instanceof Error ? err.message : "";
      setError(mensaje && mensaje !== "Failed to fetch" ? mensaje : "No se pudo conectar con el backend.");
    } finally {
      setPensando(false);
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void enviar(pregunta);
  }

  function empezarDeNuevo() {
    sessionStorage.setItem(CLAVE, "nueva");
    setConversacion(null);
    setFase("subir");
    setError("");
    setPregunta("");
    setDocumentos([]);
  }

  const leyendo =
    conversacion?.estado === "PENDING" || conversacion?.estado === "PROCESSING";
  const lista = conversacion?.estado === "READY";
  const fallo = conversacion?.estado === "FAILED";

  return (
    <main>
      <section className="relative overflow-hidden px-6 pb-8 pt-12 sm:pt-16">
        <div className="blob pointer-events-none absolute -left-16 top-8 h-56 w-56 rounded-full bg-gold/50 blur-3xl" />
        <div className="blob-late pointer-events-none absolute right-0 top-16 h-64 w-64 rounded-full bg-pine/20 blur-3xl" />

        <div className="relative mx-auto max-w-[100rem]">
          <p className="rise text-sm font-medium tracking-[0.18em] text-clay uppercase">
            Consultor IA
          </p>
          <h1 className="rise rise-1 font-display mt-4 text-5xl leading-[1.05] text-ink sm:text-6xl">
            Relacionar
          </h1>
          <div className="rise rise-2 mt-6 flex flex-wrap items-end justify-between gap-4">
            <p className="max-w-2xl text-lg leading-relaxed text-ink/75">
              Subí hasta tres documentos del proyecto. Cuando termine de leerlos, preguntame qué fondos se adecuan, qué requisitos piden o cómo es el proceso de postulación.
            </p>
            {fase === "chat" && conversacion ? (
              <button
                type="button"
                onClick={empezarDeNuevo}
                className="rounded-full bg-pine px-5 py-2.5 text-sm font-medium text-ink transition hover:bg-pine-hover"
              >
                Nueva consulta
              </button>
            ) : null}
          </div>
          <Pestanas actual="relacionar" />
        </div>
      </section>

      <section className="px-6 pb-20">
        <div className="mx-auto max-w-6xl">
          {fase === "cargando" ? (
            <p className="text-sm text-ink/60">Cargando la consulta...</p>
          ) : null}

          {fase === "subir" ? (
            <div className="grid gap-4">
              <div>
                <p className="mb-2 text-sm text-ink">
                  Documentos del proyecto
                  <span className="text-ink/55"> · hasta {LIMITE_DOCUMENTOS}</span>
                </p>
                <label
                  htmlFor="documentos-proyecto"
                  className="flex min-h-56 cursor-pointer flex-col items-center justify-center rounded-3xl border border-dashed border-pine/30 bg-paper/70 px-6 py-10 text-center transition hover:border-pine hover:bg-paper"
                >
                  <span className="text-sm text-ink/70">
                    Elegí hasta 3 documentos. PDF, Word, Excel o texto.
                  </span>
                  <input
                    id="documentos-proyecto"
                    type="file"
                    multiple
                    accept=".pdf,.docx,.xlsx,.xls,.txt,.csv"
                    className="sr-only"
                    onChange={(event) => {
                      const archivos = Array.from(event.target.files ?? []);
                      event.target.value = "";
                      elegirDocumentos(archivos);
                    }}
                  />
                </label>
              </div>

              {documentos.length > 0 ? (
                <div className="rounded-3xl border border-pine/10 bg-paper p-5 shadow-sm">
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
                          onClick={() =>
                            setDocumentos((actuales) => actuales.filter((_, i) => i !== index))
                          }
                          className="shrink-0 text-sm text-ink/50 transition hover:text-clay"
                        >
                          Quitar
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => void subir()}
                  disabled={subiendo || documentos.length === 0}
                  className="rounded-full bg-pine px-5 py-2.5 text-sm font-medium text-ink transition hover:bg-pine-hover disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {subiendo ? "Subiendo..." : "Leer documentos"}
                </button>
              </div>
            </div>
          ) : null}

          {fase === "chat" && leyendo ? (
            <div className="rounded-3xl border border-pine/15 bg-paper px-6 py-8 shadow-sm">
              <p className="font-display text-2xl text-ink">Leyendo los documentos del proyecto</p>
              <p className="mt-3 max-w-2xl text-sm leading-relaxed text-ink/70">
                Esta parte es la que demora. Estoy leyendo
                {" "}
                {conversacion?.documentos.length
                  ? conversacion.documentos.join(", ")
                  : "los documentos"}
                . Puede tardar varios minutos. Cuando termine, te pregunto en qué querés ayuda.
              </p>
            </div>
          ) : null}

          {fase === "chat" && fallo ? (
            <div className="rounded-3xl border border-clay/30 bg-paper px-6 py-8 shadow-sm">
              <p className="text-sm text-ink">{conversacion?.error || "No pude leer los documentos."}</p>
              <button
                type="button"
                onClick={empezarDeNuevo}
                className="mt-4 rounded-full bg-pine px-5 py-2.5 text-sm font-medium text-ink transition hover:bg-pine-hover"
              >
                Subir otros documentos
              </button>
            </div>
          ) : null}

          {fase === "chat" && lista ? (
            <div className="grid gap-4">
              <div
                ref={hilo}
                className="flex max-h-[32rem] flex-col gap-3 overflow-y-auto rounded-3xl border border-pine/10 bg-paper p-5 shadow-sm"
              >
                {conversacion?.mensajes.map((mensaje, index) => {
                  const propio = mensaje.rol === "usuario";
                  return (
                    <div key={`${mensaje.rol}-${index}`} className={propio ? "flex justify-end" : ""}>
                      <div
                        className={
                          propio
                            ? "max-w-[85%] rounded-3xl bg-foam px-4 py-3 text-sm leading-relaxed text-ink"
                            : "max-w-[85%] rounded-3xl bg-sand px-4 py-3 text-sm leading-relaxed text-ink"
                        }
                      >
                        <p className="whitespace-pre-wrap">{mensaje.contenido}</p>
                        {mensaje.fondos && mensaje.fondos.length > 0 ? (
                          <ul className="mt-3 flex flex-col gap-2">
                            {mensaje.fondos.map((fondo) => (
                              <li key={fondo.id}>
                                <Link
                                  href={`/repositorio/convocatorias/${fondo.id}`}
                                  className="block rounded-2xl border border-pine/20 bg-paper px-4 py-3 transition hover:border-pine"
                                >
                                  <span className="block text-sm font-medium text-ink">
                                    {fondo.titulo || `Convocatoria ${fondo.id}`}
                                  </span>
                                  {fondo.estado ? (
                                    <span className="mt-1 block text-xs text-pine-text">{fondo.estado}</span>
                                  ) : null}
                                  {fondo.motivo ? (
                                    <span className="mt-1 block text-sm text-ink/70">{fondo.motivo}</span>
                                  ) : null}
                                </Link>
                              </li>
                            ))}
                          </ul>
                        ) : null}
                      </div>
                    </div>
                  );
                })}
                {pensando ? (
                  <p className="text-sm text-ink/60">Estoy revisando los fondos y los documentos...</p>
                ) : null}
              </div>

              <div className="flex flex-wrap gap-2">
                {SUGERENCIAS.map((sugerencia) => (
                  <button
                    key={sugerencia}
                    type="button"
                    disabled={pensando}
                    onClick={() => void enviar(sugerencia)}
                    className="rounded-full border border-pine/30 bg-paper px-4 py-2 text-left text-sm text-ink/80 transition hover:border-pine hover:text-ink disabled:opacity-50"
                  >
                    {sugerencia}
                  </button>
                ))}
              </div>

              <form onSubmit={onSubmit} className="relative">
                <label htmlFor="pregunta" className="sr-only">
                  Pregunta
                </label>
                <textarea
                  id="pregunta"
                  rows={3}
                  maxLength={2000}
                  value={pregunta}
                  onChange={(event) => setPregunta(event.target.value)}
                  placeholder="Preguntá por fondos, requisitos o el proceso de postulación"
                  disabled={pensando}
                  className="w-full resize-none rounded-3xl border border-pine/20 bg-paper px-5 py-4 pr-28 text-sm text-ink shadow-sm outline-none transition focus:border-pine disabled:opacity-70"
                />
                <button
                  type="submit"
                  disabled={pensando || pregunta.trim().length < 2}
                  className="absolute right-3 bottom-3 rounded-full bg-pine px-4 py-2 text-sm font-medium text-ink transition hover:bg-pine-hover disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Preguntar
                </button>
              </form>
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm text-ink/60">
                  Las respuestas son cortas. Abrí un fondo para ver el detalle y después podés preguntar algo puntual.
                </p>
              </div>
            </div>
          ) : null}

          {error ? (
            <p className="mt-4 rounded-2xl border border-clay/30 bg-paper px-5 py-4 text-sm text-ink" role="alert">
              {error}
            </p>
          ) : null}
        </div>
      </section>
    </main>
  );
}
