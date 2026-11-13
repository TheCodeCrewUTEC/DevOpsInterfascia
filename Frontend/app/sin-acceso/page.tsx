import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Sin acceso | Interfascia",
};

export default function SinAccesoPage() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 px-6 py-16">
      <p className="text-sm font-medium tracking-[0.18em] text-clay uppercase">Acceso</p>
      <h1 className="font-display text-4xl text-ink">Esta sección no está en tu rol</h1>
      <p className="max-w-xl text-sm leading-relaxed text-ink/75">
        Tu rol no incluye esta sección. El repositorio, las alertas y el perfil siguen disponibles.
      </p>
      <Link
        href="/"
        className="mt-2 w-fit rounded-full bg-pine px-5 py-2.5 text-sm font-medium text-ink transition hover:bg-pine-hover"
      >
        Volver al inicio
      </Link>
    </main>
  );
}
