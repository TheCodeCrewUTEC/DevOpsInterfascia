import type { Metadata } from "next";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { Opciones, Preferencias, Suscripcion } from "@/lib/alertas";
import FormularioPreferencias from "./FormularioPreferencias";
import Suscripciones from "./Suscripciones";

export const metadata: Metadata = {
  title: "Preferencias de alertas | Interfascia",
};

export const dynamic = "force-dynamic";

// Trae un recurso de la API; devuelve null y anota el error si falla
async function cargar<T>(path: string, que: string, errores: string[]): Promise<T | null> {
  try {
    const response = await apiFetch(path, { cache: "no-store" });
    if (response.ok) {
      return (await response.json()) as T;
    }
    errores.push(`No se pudieron cargar ${que} (${response.status}).`);
  } catch {
    errores.push(`No se pudieron cargar ${que}: no se pudo conectar con la API.`);
  }
  return null;
}

export default async function PreferenciasAlertasPage() {
  const errores: string[] = [];
  const [preferencias, suscripciones, opciones] = await Promise.all([
    cargar<Preferencias>("/api/alertas/preferencias", "tus preferencias", errores),
    cargar<Suscripcion[]>("/api/alertas/suscripciones", "tus suscripciones", errores),
    cargar<Opciones>("/api/alertas/opciones", "las opciones", errores),
  ]);

  return (
    <main className="mx-auto flex w-full max-w-[100rem] flex-1 flex-col gap-6 px-6 py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium tracking-[0.18em] text-clay uppercase">Mi cuenta</p>
          <h1 className="font-display mt-2 text-4xl text-ink">Preferencias de alertas</h1>
          <p className="mt-2 text-sm text-ink/70">
            Elegí qué avisos recibir y qué fondos, instituciones o áreas temáticas seguir.
          </p>
        </div>
        <Link
          href="/alertas"
          className="rounded-full border-2 border-ink px-4 py-2 text-sm text-ink transition hover:bg-foam"
        >
          Ver mis alertas
        </Link>
      </div>

      {errores.map((error) => (
        <p key={error} role="alert" className="rounded-2xl border border-clay/30 bg-clay/10 px-4 py-3 text-sm text-ink">
          {error}
        </p>
      ))}

      <div className="grid gap-6 lg:grid-cols-2 lg:items-start">
        {preferencias ? <FormularioPreferencias preferencias={preferencias} /> : null}
        {suscripciones ? (
          <Suscripciones
            iniciales={suscripciones}
            opciones={opciones ?? { tipos_alerta: [], tematicas: [], instituciones: [] }}
          />
        ) : null}
      </div>
    </main>
  );
}
