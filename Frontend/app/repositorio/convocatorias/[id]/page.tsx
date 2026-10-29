import { notFound } from "next/navigation";
import { auth } from "@/auth";
import { Seccion, Volver, enlaceFuente, fecha, pesos, texto } from "../../ficha";
import SuscripcionBotones from "./SuscripcionBotones";

const API_URL = (process.env.API_URL ?? "http://localhost:8000").replace(/\/$/, "");

type Documento = {
  id: number;
  nombre: string | null;
  url: string | null;
};

type Convocatoria = {
  id: number;
  titulo: string | null;
  institucion: string | null;
  estado: string | null;
  fecha_apertura: string | null;
  fecha_cierre: string | null;
  descripcion: string | null;
  beneficiarios: string | null;
  requisitos: string | null;
  financiamiento: number | string | null;
  fuente: string | null;
  documentos: Documento[];
};

export const dynamic = "force-dynamic";

export default async function PaginaConvocatoria({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) notFound();

  const response = await fetch(`${API_URL}/api/convocatorias/${id}`, { cache: "no-store" });
  if (response.status === 404) notFound();
  if (!response.ok) {
    return (
      <main className="px-6 py-16">
        <p className="text-clay">No se pudo cargar la convocatoria.</p>
      </main>
    );
  }

  const convocatoria = (await response.json()) as Convocatoria;
  const documentos = convocatoria.documentos ?? [];
  const fuente = enlaceFuente(convocatoria.fuente);
  const session = await auth();
  const logueado = Boolean(session?.user) && !session?.error;

  return (
    <main>
      <section className="relative overflow-hidden px-6 pb-10 pt-12 sm:pt-16">
        <div className="blob pointer-events-none absolute -left-16 top-8 h-56 w-56 rounded-full bg-gold/50 blur-3xl" />
        <div className="relative mx-auto max-w-3xl">
          <Volver href="/repositorio">Volver al repositorio</Volver>
          <p className="mt-6 text-sm font-medium tracking-[0.18em] text-clay uppercase">Convocatoria</p>
          <h1 className="font-display mt-4 text-4xl leading-[1.1] text-ink sm:text-5xl">
            {texto(convocatoria.titulo)}
          </h1>
          <p className="mt-4 text-lg text-ink/75">{texto(convocatoria.institucion)}</p>
          {fuente ? (
            <a
              href={fuente.href}
              target="_blank"
              rel="noreferrer"
              className="mt-4 inline-flex text-sm text-pine-text underline-offset-2 hover:underline"
            >
              Fuente · {fuente.etiqueta}
            </a>
          ) : null}
          <div className="mt-6">
            <SuscripcionBotones
              convocatoriaId={convocatoria.id}
              institucion={convocatoria.institucion?.trim() || null}
              logueado={logueado}
            />
          </div>
        </div>
      </section>

      <section className="px-6 pb-20">
        <div className="mx-auto flex max-w-3xl flex-col gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Seccion titulo="Estado">{texto(convocatoria.estado)}</Seccion>
            <Seccion titulo="Financiamiento">{pesos(convocatoria.financiamiento)}</Seccion>
            <Seccion titulo="Apertura">{fecha(convocatoria.fecha_apertura)}</Seccion>
            <Seccion titulo="Cierre">{fecha(convocatoria.fecha_cierre)}</Seccion>
          </div>
          <Seccion titulo="Descripción">{texto(convocatoria.descripcion)}</Seccion>
          <Seccion titulo="Beneficiarios">{texto(convocatoria.beneficiarios)}</Seccion>
          <Seccion titulo="Requisitos">{texto(convocatoria.requisitos)}</Seccion>
          <Seccion titulo="Documentos">
            {documentos.length === 0 ? (
              "Sin documentos"
            ) : (
              <ul className="flex flex-col gap-2">
                {documentos.map((documento) => (
                  <li key={documento.id}>
                    {documento.url ? (
                      <a
                        href={documento.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-pine-text underline-offset-2 hover:underline"
                      >
                        {texto(documento.nombre)}
                      </a>
                    ) : (
                      texto(documento.nombre)
                    )}
                  </li>
                ))}
              </ul>
            )}
          </Seccion>
        </div>
      </section>
    </main>
  );
}
