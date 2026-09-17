import Link from "next/link";

export default function LoginPage() {
  return (
    <main className="flex flex-1 items-center justify-center bg-neutral-700 px-4 py-10">

      <div className="relative w-full max-w-md bg-white px-10 py-12">

        {/* Cerrar */}
        <Link
          href="/"
          className="absolute right-5 top-4 text-2xl leading-none text-black"
          aria-label="Cerrar"
        >
          ×
        </Link>

        <h1 className="mb-10 text-center text-3xl font-bold text-black">
          Iniciar Sesión
        </h1>

        <form className="flex flex-col gap-5">

          <div className="flex flex-col gap-2">
            <label htmlFor="usuario" className="text-sm text-black">
              Nombre de usuario / Email
            </label>
            <input
              id="usuario"
              name="usuario"
              type="text"
              className="h-10 border border-black bg-neutral-400 px-3 outline-none"
              required
            />
          </div>

          <div className="flex flex-col gap-2">
            <label htmlFor="contrasena" className="text-sm text-black">
              Contraseña
            </label>
            <input
              id="contrasena"
              name="contrasena"
              type="password"
              className="h-10 border border-black bg-neutral-400 px-3 outline-none"
              required
            />
          </div>

          <Link
            href="#"
            className="mt-1 text-center text-sm text-black underline"
          >
            ¿Olvidaste tu contraseña?
          </Link>

          <button
            type="submit"
            className="mx-auto mt-2 w-48 border border-black bg-neutral-300 py-2 text-center text-black"
          >
            Iniciar Sesión
          </button>

          <Link
            href="/registro"
            className="mt-2 text-center text-sm text-black underline"
          >
            ¿No tienes una cuenta aún? Registrate ahora
          </Link>

          <button
            type="button"
            className="mt-4 flex w-full items-center justify-center gap-3 border border-black bg-neutral-300 py-2.5 text-black"
          >
            <GoogleIcon />
            Continuar con Google
          </button>

        </form>

      </div>

    </main>
  );
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
      <path
        fill="#FFC107"
        d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34.2 6.1 29.4 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.5-.4-3.5z"
      />
      <path
        fill="#FF3D00"
        d="M6.3 14.7l6.6 4.8C14.7 16.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34.2 6.1 29.4 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"
      />
      <path
        fill="#4CAF50"
        d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.3 26.7 36 24 36c-5.3 0-9.7-3.3-11.3-7.9l-6.5 5C9.6 39.6 16.2 44 24 44z"
      />
      <path
        fill="#1976D2"
        d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.1-4.1 5.5l.1.1 6.2 5.2C39.2 37.1 44 32 44 24c0-1.3-.1-2.5-.4-3.5z"
      />
    </svg>
  );
}
