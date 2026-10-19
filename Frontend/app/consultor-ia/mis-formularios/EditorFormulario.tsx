"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import FormularioCompletado from "../FormularioCompletado";
import type { CampoFormulario, Fuente } from "../formulario";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";

type Resultado = {
  estado: string;
  respuestas: CampoFormulario[];
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

export default function EditorFormulario({ jobId }: { jobId: number }) {
  const router = useRouter();
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let activo = true;
    let espera = 0;

    async function cargar() {
      try {
        const response = await fetch(`${API_URL}/formularios/jobs/${jobId}/resultado`, {
          credentials: "include",
          cache: "no-store",
        });
        if (response.status === 404) {
          throw new Error("No encontramos ese formulario.");
        }
        if (!response.ok) {
          throw new Error("No se pudo abrir el formulario.");
        }

        const datos = (await response.json()) as {
          estado: string;
          respuestas?: Array<Omit<CampoFormulario, "fuentes"> & { fuentes: unknown }>;
        };
        if (!activo) return;

        setResultado({
          estado: datos.estado,
          respuestas: (datos.respuestas ?? []).map((item) => ({
            ...item,
            respuesta_ia: item.respuesta_ia ?? null,
            editada: Boolean(item.editada),
            tipo: item.tipo ?? null,
            pagina: item.pagina ?? null,
            fuentes: normalizarFuentes(item.fuentes),
          })),
        });
        setError(null);

        const termino = datos.estado === "COMPLETED" || datos.estado === "FAILED";
        if (activo && !termino) {
          espera = window.setTimeout(() => void cargar(), 5000);
        }
      } catch (err) {
        if (!activo) return;
        setError(err instanceof Error ? err.message : "No se pudo abrir el formulario.");
      }
    }

    void cargar();

    return () => {
      activo = false;
      window.clearTimeout(espera);
    };
  }, [jobId]);

  if (error) {
    return (
      <main className="px-6 py-16">
        <div className="mx-auto max-w-3xl">
          <p role="alert" className="text-clay">
            {error}
          </p>
          <Link href="/consultor-ia/mis-formularios" className="mt-6 inline-flex text-sm text-pine-text">
            Volver a Mis formularios
          </Link>
        </div>
      </main>
    );
  }

  if (resultado?.estado === "FAILED") {
    return (
      <main className="px-6 py-16">
        <div className="mx-auto max-w-3xl">
          <h1 className="font-display text-4xl text-ink">No se pudo completar</h1>
          <p className="mt-4 text-ink/75">Este formulario no terminó de procesarse.</p>
          <Link href="/consultor-ia/mis-formularios" className="mt-6 inline-flex text-sm text-pine-text">
            Volver a Mis formularios
          </Link>
        </div>
      </main>
    );
  }

  if (resultado?.estado === "COMPLETED") {
    return (
      <main>
        <section className="relative overflow-hidden px-6 pb-8 pt-12 sm:pt-16">
          <div className="relative mx-auto max-w-6xl">
            <p className="text-sm font-medium tracking-[0.18em] text-clay uppercase">
              Consultor IA · Mis formularios
            </p>
            <h1 className="font-display mt-4 text-5xl leading-[1.05] text-ink sm:text-6xl">
              Formulario generado
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-ink/75">
              Corregí las respuestas, guardalas y descargá el PDF.
            </p>
          </div>
        </section>
        <section className="px-6 pb-20">
          <div className="mx-auto max-w-4xl">
            <FormularioCompletado
              jobId={jobId}
              campos={resultado.respuestas}
              onVolver={() => router.push("/consultor-ia/mis-formularios")}
            />
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="px-6 py-16">
      <div className="mx-auto max-w-3xl">
        <p className="text-sm font-medium tracking-[0.18em] text-clay uppercase">En proceso</p>
        <h1 className="font-display mt-4 text-5xl text-ink">Estamos completando el formulario</h1>
        <p className="mt-4 max-w-xl text-lg text-ink/75">
          Te avisamos con una notificación cuando esté listo. Podés salir de esta página: va a
          quedar en Mis formularios.
        </p>
        <Link
          href="/consultor-ia/mis-formularios"
          className="mt-8 inline-flex rounded-full border border-pine/30 bg-paper px-4 py-2 text-sm text-ink"
        >
          Volver a Mis formularios
        </Link>
      </div>
    </main>
  );
}
