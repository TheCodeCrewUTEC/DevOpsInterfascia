import type { Metadata } from "next";
import { apiFetch } from "@/lib/api";
import FormularioPerfil, { type Perfil } from "./FormularioPerfil";

export const metadata: Metadata = {
  title: "Mi perfil | Interfascia",
};

export const dynamic = "force-dynamic";

export default async function PerfilPage() {
  let perfil: Perfil | null = null;
  let error: string | null = null;

  try {
    const response = await apiFetch("/api/perfil", { cache: "no-store" });
    if (response.ok) {
      perfil = (await response.json()) as Perfil;
    } else {
      error = `No se pudieron cargar tus datos (${response.status}).`;
    }
  } catch {
    error = "No se pudo conectar con la API.";
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-6 py-10">
      <div>
        <p className="text-sm font-medium tracking-[0.18em] text-clay uppercase">Mi cuenta</p>
        <h1 className="font-display mt-2 text-4xl text-ink">Mi perfil</h1>
        <p className="mt-2 text-sm text-ink/70">
          Actualizá tus datos. El rol solo lo puede cambiar un administrador.
        </p>
      </div>

      {error ? (
        <p role="alert" className="rounded-2xl border border-clay/30 bg-clay/10 px-4 py-3 text-sm text-ink">
          {error}
        </p>
      ) : null}

      {perfil ? <FormularioPerfil perfil={perfil} /> : null}
    </main>
  );
}
