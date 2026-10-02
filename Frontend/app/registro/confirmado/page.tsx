import type { Metadata } from "next";
import RedireccionLogin from "./RedireccionLogin";

export const metadata: Metadata = {
  title: "Registro exitoso | Interfascia",
};

const SEGUNDOS = 5;

export default function RegistroConfirmadoPage() {
  return (
    <main className="flex flex-1 items-center justify-center bg-neutral-700 px-4 py-10">

      <div className="w-full max-w-md bg-white px-10 py-12 text-center" role="status">

        <div
          className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-full border-2 border-black text-3xl text-black"
          aria-hidden="true"
        >
          ✓
        </div>

        <h1 className="mb-4 text-3xl font-bold text-black">
          ¡Registro exitoso!
        </h1>

        <p className="mb-8 text-sm text-black">
          Tu cuenta fue creada correctamente. Iniciá sesión con tu email y contraseña para ingresar.
        </p>

        {/* Enlace normal (no Link): /login es una ruta que redirige a Keycloak */}
        <a
          href="/login"
          className="mx-auto block w-48 border border-black bg-neutral-300 py-2 text-black"
        >
          Iniciar Sesión
        </a>

        <RedireccionLogin segundos={SEGUNDOS} />

      </div>

    </main>
  );
}
