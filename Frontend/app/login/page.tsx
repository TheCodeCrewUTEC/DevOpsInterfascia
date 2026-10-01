"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { guardarSesion } from "../lib/sesion";

const requiredFields = ["usuario", "contrasena"];

const campo =
  "h-11 rounded-xl border border-pine/20 bg-foam/70 px-3 text-sm text-ink outline-none transition focus:border-pine focus:bg-paper";

const campoInvalido =
  "h-11 rounded-xl border border-red-600 bg-red-50 px-3 text-sm text-ink outline-none transition focus:border-red-600";

function missingRequired(form: HTMLFormElement) {
  const data = new FormData(form);
  return requiredFields.filter((name) =>
    data.getAll(name).every((value) => String(value).trim() === ""),
  );
}

export default function LoginPage() {
  const [attempted, setAttempted] = useState(false);
  const [empty, setEmpty] = useState<string[]>([]);

  function iniciar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const missing = missingRequired(event.currentTarget);
    setAttempted(true);
    setEmpty(missing);

    if (missing.length === 0) {
      const usuario = String(new FormData(event.currentTarget).get("usuario") ?? "").trim();
      guardarSesion(usuario);

      const siguiente = new URLSearchParams(window.location.search).get("siguiente");
      if (siguiente?.startsWith("/") && !siguiente.startsWith("//")) {
        window.location.assign(siguiente);
      }
      return;
    }

    const first = event.currentTarget.elements.namedItem(missing[0]);
    if (first instanceof HTMLElement) first.focus();
  }

  function actualizar(event: FormEvent<HTMLFormElement>) {
    if (!attempted) return;
    setEmpty(missingRequired(event.currentTarget));
  }

  function invalido(name: string) {
    return empty.includes(name);
  }

  return (
    <main className="relative flex flex-1 items-center justify-center overflow-hidden px-4 py-16">
      <div className="blob pointer-events-none absolute -left-16 top-10 h-56 w-56 rounded-full bg-gold/40 blur-3xl" />
      <div className="blob-late pointer-events-none absolute right-0 bottom-0 h-64 w-64 rounded-full bg-pine/20 blur-3xl" />

      <div className="relative w-full max-w-md rounded-[2rem] bg-paper px-8 py-10 shadow-sm ring-1 ring-pine/10 sm:px-10">
        <Link
          href="/"
          className="absolute right-5 top-5 flex h-8 w-8 items-center justify-center rounded-full text-xl text-ink/60 transition hover:bg-foam hover:text-ink"
          aria-label="Cerrar"
        >
          ×
        </Link>

        {empty.length > 0 ? (
          <p className="mb-4 pr-8 text-sm font-medium text-red-600" role="alert">
            Los campos resaltados son obligatorios
          </p>
        ) : null}

        <p className="text-xs font-medium tracking-[0.16em] text-clay uppercase">
          Cuenta
        </p>
        <h1 className="font-display mt-2 text-4xl text-ink">Iniciar sesión</h1>
        <p className="mt-2 text-sm leading-relaxed text-ink/70">
          Entrá para consultar fondos, proyectos e investigadores.
        </p>

        <form className="mt-8 flex flex-col gap-5" onSubmit={iniciar} onChange={actualizar} noValidate>
          <div className="flex flex-col gap-2">
            <label htmlFor="usuario" className={invalido("usuario") ? "text-sm text-red-600" : "text-sm text-ink"}>
              Nombre de usuario / Email
            </label>
            <input
              id="usuario"
              name="usuario"
              type="text"
              autoComplete="username"
              aria-invalid={invalido("usuario")}
              aria-required
              className={invalido("usuario") ? campoInvalido : campo}
            />
          </div>

          <div className="flex flex-col gap-2">
            <label htmlFor="contrasena" className={invalido("contrasena") ? "text-sm text-red-600" : "text-sm text-ink"}>
              Contraseña
            </label>
            <input
              id="contrasena"
              name="contrasena"
              type="password"
              autoComplete="current-password"
              aria-invalid={invalido("contrasena")}
              aria-required
              className={invalido("contrasena") ? campoInvalido : campo}
            />
          </div>

          <Link
            href="#"
            className="text-sm text-pine-text underline-offset-4 hover:underline"
          >
            ¿Olvidaste tu contraseña?
          </Link>

          <button
            type="submit"
            className="rounded-full bg-pine py-3 text-sm font-medium text-ink shadow-sm transition duration-200 hover:-translate-y-0.5 hover:bg-pine-hover"
          >
            Iniciar sesión
          </button>

          <button
            type="button"
            className="flex w-full items-center justify-center gap-3 rounded-full border border-pine/30 bg-paper py-3 text-sm text-ink transition duration-200 hover:-translate-y-0.5 hover:border-pine hover:bg-foam"
          >
            <GoogleIcon />
            Continuar con Google
          </button>

          <p className="text-center text-sm text-ink/70">
            ¿No tienes una cuenta aún?{" "}
            <Link href="/registro" className="text-pine-text underline-offset-4 hover:underline">
              Registrate ahora
            </Link>
          </p>
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
