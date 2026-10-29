import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { auth } from "@/auth";
import { apiFetch } from "@/lib/api";
import { formatFecha } from "@/lib/suscripciones";
import SuscripcionBotones from "./SuscripcionBotones";

export const metadata: Metadata = {
  title: "Detalle del fondo | Interfascia",
};

export const dynamic = "force-dynamic";

type Documento = {
  id: number;
  nombre: string | null;
  url: string | null;
};

type ConvocatoriaDetalle = {
  id: number;
  titulo: string | null;
  institucion: string | null;
  estado: string | null;
  fecha_apertura: string | null;
  fecha_cierre: string | null;
  descripcion: string | null;
  beneficiarios: string | null;
  requisitos: string | null;
  financiamiento: number | null;
  documentos: Documento[];
};

function texto(valor: string | null | undefined, vacio: string) {
  const limpio = valor?.trim();
  return limpio ? limpio : vacio;
}

function formatMonto(valor: number | null) {
  if (valor === null || valor === undefined) return "Sin datos";
  return `$ ${valor.toLocaleString("es-UY")}`;
}

export default async function ConvocatoriaPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) notFound();

  let convocatoria: ConvocatoriaDetalle | null = null;
  let error: string | null = null;
  let noExiste = false;

  try {
    const response = await apiFetch(`/api/convocatorias/${id}`, { cache: "no-store" });
    if (response.status === 404) {
      noExiste = true;
    } else if (response.ok) {
      convocatoria = (await response.json()) as ConvocatoriaDetalle;
    } else {
      error = `No se pudo cargar el fondo (${response.status}).`;
    }
  } catch {
    error = "No se pudo conectar con la API.";
  }

  // Fuera del try: notFound() lanza una excepción que Next tiene que recibir
  if (noExiste) notFound();

  const session = await auth();
  const logueado = Boolean(session?.user) && !session?.error;

  return (
    <main className="px-6 pb-20 pt-10">
      <div className="mx-auto flex max-w-[100rem] flex-col gap-6">
        <Link
          href="/repositorio"
          className="inline-flex min-h-11 w-fit items-center gap-1.5 text-sm text-pine-text underline-offset-4 hover:underline"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M10 3.5 5.5 8l4.5 4.5" />
          </svg>
          Volver al repositorio
        </Link>

        {error ? (
          <p role="alert" className="rounded-2xl border border-clay/30 bg-clay/10 px-4 py-3 text-sm text-ink">
            {error}
          </p>
        ) : null}

        {convocatoria ? (
          <>
            <div>
              <p className="text-sm font-medium tracking-[0.18em] text-clay uppercase">
                Convocatoria · {texto(convocatoria.institucion, "Sin institución")}
              </p>
              <h1 className="font-display mt-3 text-4xl leading-tight text-balance break-words text-ink sm:text-5xl">
                {texto(convocatoria.titulo, "Sin título")}
              </h1>
              <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm text-ink/80">
                <p>
                  <span className="text-pine-text">Estado</span> · {texto(convocatoria.estado, "Sin estado")}
                </p>
                <p>
                  <span className="text-pine-text">Apertura</span> · {formatFecha(convocatoria.fecha_apertura)}
                </p>
                <p>
                  <span className="text-pine-text">Cierre</span> · {formatFecha(convocatoria.fecha_cierre)}
                </p>
              </div>
            </div>

            <SuscripcionBotones
              convocatoriaId={convocatoria.id}
              institucion={convocatoria.institucion?.trim() || null}
              logueado={logueado}
            />

            <div className="grid gap-6 lg:grid-cols-[1.6fr_0.9fr]">
              <div className="flex flex-col gap-6">
                <Seccion titulo="Descripción" contenido={texto(convocatoria.descripcion, "Sin descripción")} />
                <Seccion titulo="Beneficiarios" contenido={texto(convocatoria.beneficiarios, "Sin datos")} />
                <Seccion titulo="Requisitos" contenido={texto(convocatoria.requisitos, "Sin datos")} />
              </div>

              <aside className="flex h-fit flex-col gap-6">
                <Seccion titulo="Financiamiento" contenido={formatMonto(convocatoria.financiamiento)} />

                <section className="rounded-3xl border-2 border-ink bg-paper p-5 sm:p-6">
                  <h2 className="font-display text-2xl text-ink">Documentos</h2>
                  {convocatoria.documentos.length === 0 ? (
                    <p className="mt-3 text-sm text-ink/70">No hay documentos cargados.</p>
                  ) : (
                    <ul className="mt-3 flex flex-col gap-2 text-sm">
                      {convocatoria.documentos.map((documento) => {
                        const nombre = texto(documento.nombre, "Documento sin nombre");
                        return (
                          <li key={documento.id}>
                            {documento.url ? (
                              <a
                                href={documento.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex min-h-9 items-center break-all text-pine-text underline-offset-4 hover:underline pointer-coarse:min-h-11"
                              >
                                {nombre}
                              </a>
                            ) : (
                              <span className="text-ink/80">{nombre}</span>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </section>
              </aside>
            </div>
          </>
        ) : null}
      </div>
    </main>
  );
}

function Seccion({ titulo, contenido }: { titulo: string; contenido: string }) {
  return (
    <section className="rounded-3xl border-2 border-ink bg-paper p-5 sm:p-6">
      <h2 className="font-display text-2xl text-ink">{titulo}</h2>
      <p className="mt-3 whitespace-pre-line text-sm leading-relaxed text-ink/80">{contenido}</p>
    </section>
  );
}
