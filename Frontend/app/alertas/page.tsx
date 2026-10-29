import type { Metadata } from "next";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { LIMITE_NOTIFICACIONES, type PaginaNotificaciones } from "@/lib/alertas";
import ListaNotificaciones from "./ListaNotificaciones";

export const metadata: Metadata = {
  title: "Mis alertas | Interfascia",
};

export const dynamic = "force-dynamic";

export default async function AlertasPage() {
  let pagina: PaginaNotificaciones | null = null;
  let error: string | null = null;

  try {
    const response = await apiFetch(`/api/alertas/notificaciones?page=1&limit=${LIMITE_NOTIFICACIONES}`, { cache: "no-store" });
    if (response.ok) {
      pagina = (await response.json()) as PaginaNotificaciones;
    } else {
      error = `No se pudieron cargar tus alertas (${response.status}).`;
    }
  } catch {
    error = "No se pudo conectar con la API.";
  }

  return (
    <main className="mx-auto flex w-full max-w-[100rem] flex-1 flex-col gap-6 px-6 py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium tracking-[0.18em] text-clay uppercase">Mi cuenta</p>
          <h1 className="font-display mt-2 text-4xl text-balance text-ink">Mis alertas</h1>
          <p className="mt-2 text-sm text-ink/70">
            Avisos de apertura, cierre y cambios de los fondos que seguís.
          </p>
        </div>
        <Link
          href="/alertas/preferencias"
          className="presionable inline-flex min-h-11 items-center rounded-full border-2 border-ink px-4 text-sm text-ink hover:bg-foam"
        >
          Preferencias de alertas
        </Link>
      </div>

      {error ? (
        <p role="alert" className="rounded-2xl border border-clay/30 bg-clay/10 px-4 py-3 text-sm text-ink">
          {error}
        </p>
      ) : null}

      {pagina ? <ListaNotificaciones inicial={pagina} /> : null}
    </main>
  );
}
