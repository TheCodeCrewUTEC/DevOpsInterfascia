"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Pestanas from "../Pestanas";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";

type Formulario = {
  id: number;
  estado: string;
  creado: string;
  nombre: string | null;
  en_proceso: boolean;
};

function etiqueta(formulario: Formulario) {
  if (formulario.estado === "COMPLETED") return "Listo";
  if (formulario.estado === "FAILED") return "No se pudo completar";
  if (formulario.en_proceso) return "En proceso";
  if (formulario.estado === "PROCESSING") return "Procesando";
  return "En cola";
}

function tono(formulario: Formulario) {
  if (formulario.estado === "COMPLETED") return "bg-foam text-pine-text";
  if (formulario.estado === "FAILED") return "bg-clay/10 text-clay";
  if (formulario.en_proceso) return "bg-gold/40 text-ink";
  return "bg-sand text-ink/80";
}

function fecha(valor: string) {
  const momento = new Date(valor);
  if (Number.isNaN(momento.getTime())) return "";
  return momento.toLocaleString("es-UY", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function MisFormulariosPage() {
  const [formularios, setFormularios] = useState<Formulario[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let activo = true;

    async function cargar() {
      try {
        const response = await fetch(`${API_URL}/formularios/jobs`, {
          credentials: "include",
          cache: "no-store",
        });
        if (!response.ok) {
          throw new Error("No se pudieron cargar tus formularios.");
        }
        const lista = (await response.json()) as Formulario[];
        if (activo) {
          setFormularios(lista);
          setError(null);
        }
      } catch (err) {
        if (!activo) return;
        setError(err instanceof Error ? err.message : "No se pudieron cargar tus formularios.");
      }
    }

    void cargar();
    const id = window.setInterval(() => void cargar(), 15000);
    return () => {
      activo = false;
      window.clearInterval(id);
    };
  }, []);

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
            Mis formularios
          </h1>
          <p className="rise rise-2 mt-6 max-w-2xl text-lg leading-relaxed text-ink/75">
            Acá quedan los formularios que generaste y los que siguen en proceso. Cuando uno está
            listo podés corregir las respuestas y descargarlo en PDF.
          </p>
          <Pestanas actual="formularios" />

          {error ? (
            <p role="alert" className="mt-8 text-sm text-clay">
              {error}
            </p>
          ) : null}

          {formularios == null && !error ? (
            <p className="mt-8 text-sm text-ink/70">Cargando tus formularios.</p>
          ) : null}

          {formularios?.length === 0 ? (
            <div className="mt-8 rounded-3xl border border-pine/10 bg-paper p-6 shadow-sm">
              <p className="text-ink/80">Todavía no generaste formularios.</p>
              <Link
                href="/consultor-ia/postular"
                className="mt-4 inline-flex rounded-full bg-pine px-4 py-2 text-sm font-medium text-ink"
              >
                Postular
              </Link>
            </div>
          ) : null}

          {formularios && formularios.length > 0 ? (
            <ul className="mt-8 flex flex-col gap-3">
              {formularios.map((formulario) => {
                const texto = etiqueta(formulario);
                const sePuedeAbrir = formulario.estado !== "FAILED";
                const contenido = (
                  <>
                    <div className="min-w-0">
                      <p className="truncate text-base text-ink">
                        {formulario.nombre ?? `Formulario ${formulario.id}`}
                      </p>
                      <p className="mt-1 text-sm text-ink/60">{fecha(formulario.creado)}</p>
                    </div>
                    <span className={`shrink-0 rounded-full px-3 py-1 text-sm ${tono(formulario)}`}>
                      {texto}
                    </span>
                  </>
                );

                return (
                  <li key={formulario.id}>
                    {sePuedeAbrir ? (
                      <Link
                        href={`/consultor-ia/mis-formularios/${formulario.id}`}
                        className="flex items-center justify-between gap-4 rounded-3xl border border-pine/10 bg-paper px-5 py-4 shadow-sm transition hover:border-pine/40"
                      >
                        {contenido}
                      </Link>
                    ) : (
                      <div className="flex items-center justify-between gap-4 rounded-3xl border border-pine/10 bg-paper px-5 py-4 shadow-sm">
                        {contenido}
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          ) : null}
        </div>
      </section>
    </main>
  );
}
