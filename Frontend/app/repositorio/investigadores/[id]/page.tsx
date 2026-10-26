import { notFound } from "next/navigation";
import { Seccion, Volver, enlaceFuente, texto } from "../../ficha";

const API_URL = (process.env.API_URL ?? "http://localhost:8000").replace(/\/$/, "");

type Investigador = {
  nombre: string | null;
  apellido: string | null;
  institucion: string | null;
  titulo: string | null;
  investigaciones: string | null;
  nivel_sni: string | null;
  categoria_sni: string | null;
  fuente: string | null;
};

export const dynamic = "force-dynamic";

export default async function PaginaInvestigador({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) notFound();

  const response = await fetch(`${API_URL}/api/investigadores/${id}`, { cache: "no-store" });
  if (response.status === 404) notFound();
  if (!response.ok) {
    return (
      <main className="px-6 py-16">
        <p className="text-clay">No se pudo cargar el investigador.</p>
      </main>
    );
  }

  const persona = (await response.json()) as Investigador;
  const nombre = [persona.nombre, persona.apellido].filter((parte) => parte?.trim()).join(" ");
  const fuente = enlaceFuente(persona.fuente);

  return (
    <main>
      <section className="relative overflow-hidden px-6 pb-10 pt-12 sm:pt-16">
        <div className="blob pointer-events-none absolute -left-16 top-8 h-56 w-56 rounded-full bg-gold/50 blur-3xl" />
        <div className="relative mx-auto max-w-3xl">
          <Volver href="/repositorio">Volver al repositorio</Volver>
          <p className="mt-6 text-sm font-medium tracking-[0.18em] text-clay uppercase">Investigador</p>
          <h1 className="font-display mt-4 text-4xl leading-[1.1] text-ink sm:text-5xl">
            {nombre || "Sin nombre"}
          </h1>
          <p className="mt-4 text-lg text-ink/75">{texto(persona.institucion)}</p>
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
        </div>
      </section>

      <section className="px-6 pb-20">
        <div className="mx-auto flex max-w-3xl flex-col gap-4">
          <Seccion titulo="Título">{texto(persona.titulo)}</Seccion>
          <div className="grid gap-4 sm:grid-cols-2">
            <Seccion titulo="Nivel">{texto(persona.nivel_sni)}</Seccion>
            <Seccion titulo="Categoría">{texto(persona.categoria_sni)}</Seccion>
          </div>
          <Seccion titulo="Investigaciones">{texto(persona.investigaciones)}</Seccion>
        </div>
      </section>
    </main>
  );
}
