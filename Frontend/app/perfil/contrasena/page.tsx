import type { Metadata } from "next";
import FormularioContrasena from "./FormularioContrasena";

export const metadata: Metadata = {
  title: "Cambiar contraseña | Interfascia",
};

export default function ContrasenaPage() {
  return (
    <main className="mx-auto flex w-full max-w-xl flex-1 flex-col gap-6 px-6 py-10">
      <div>
        <p className="text-sm font-medium tracking-[0.18em] text-clay uppercase">Mi cuenta</p>
        <h1 className="font-display mt-2 text-4xl text-ink">Cambiar contraseña</h1>
        <p className="mt-2 text-sm text-ink/70">
          Después del cambio se cierra tu sesión y tenés que entrar con la contraseña nueva.
        </p>
      </div>

      <FormularioContrasena />
    </main>
  );
}
