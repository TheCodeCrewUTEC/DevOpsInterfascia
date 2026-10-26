"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Button from "../../../components/Button";
import { buscarSuscripcion, type Suscripcion, type TipoSuscripcion } from "@/lib/suscripciones";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";

type Props = {
  convocatoriaId: number;
  institucion: string | null;
  logueado: boolean;
};

async function mensajeError(response: Response, porDefecto: string) {
  try {
    const cuerpo = (await response.json()) as { detail?: unknown };
    if (typeof cuerpo.detail === "string" && cuerpo.detail) return cuerpo.detail;
  } catch {
    // Sin cuerpo JSON: usamos el mensaje genérico
  }
  return `${porDefecto} (${response.status}).`;
}

export default function SuscripcionBotones({ convocatoriaId, institucion, logueado }: Props) {
  const [suscripciones, setSuscripciones] = useState<Suscripcion[]>([]);
  const [cargando, setCargando] = useState(logueado);
  // Qué botón está esperando respuesta
  const [enCurso, setEnCurso] = useState<TipoSuscripcion | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!logueado) return;
    const controlador = new AbortController();

    async function cargar() {
      try {
        const response = await fetch(`${API_URL}/api/alertas/suscripciones`, {
          signal: controlador.signal,
          cache: "no-store",
        });
        if (!response.ok) {
          throw new Error(await mensajeError(response, "No se pudieron cargar tus alertas"));
        }
        setSuscripciones((await response.json()) as Suscripcion[]);
      } catch (err) {
        if (controlador.signal.aborted) return;
        const mensaje = err instanceof Error ? err.message : "";
        setError(mensaje && mensaje !== "Failed to fetch" ? mensaje : "No se pudo conectar con el backend.");
      } finally {
        if (!controlador.signal.aborted) setCargando(false);
      }
    }

    void cargar();
    return () => controlador.abort();
  }, [logueado]);

  if (!logueado) {
    return (
      <div className="flex flex-wrap items-center gap-3">
        {/* Navegación completa: /login redirige a Keycloak */}
        <Button
          href={`/login?callbackUrl=${encodeURIComponent(`/repositorio/convocatorias/${convocatoriaId}`)}`}
          recargar
        >
          Iniciá sesión para seguir este fondo
        </Button>
      </div>
    );
  }

  const deFondo = buscarSuscripcion(suscripciones, "convocatoria", { convocatoriaId });
  const deInstitucion = institucion
    ? buscarSuscripcion(suscripciones, "institucion", { valor: institucion })
    : null;

  async function alternar(tipo: TipoSuscripcion, actual: Suscripcion | null) {
    setEnCurso(tipo);
    setError(null);
    try {
      if (actual) {
        const response = await fetch(`${API_URL}/api/alertas/suscripciones/${actual.id}`, { method: "DELETE" });
        // 404: ya no existía, el resultado es el mismo
        if (!response.ok && response.status !== 404) {
          throw new Error(await mensajeError(response, "No se pudo quitar la alerta"));
        }
        setSuscripciones((lista) => lista.filter((item) => item.id !== actual.id));
      } else {
        const response = await fetch(`${API_URL}/api/alertas/suscripciones`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(
            tipo === "convocatoria" ? { tipo, convocatoria_id: convocatoriaId } : { tipo, valor: institucion },
          ),
        });
        if (!response.ok) {
          throw new Error(await mensajeError(response, "No se pudo crear la alerta"));
        }
        const creada = (await response.json()) as Suscripcion;
        setSuscripciones((lista) => [...lista.filter((item) => item.id !== creada.id), creada]);
      }
    } catch (err) {
      const mensaje = err instanceof Error ? err.message : "";
      setError(mensaje && mensaje !== "Failed to fetch" ? mensaje : "No se pudo conectar con el backend.");
    } finally {
      setEnCurso(null);
    }
  }

  const ocupado = cargando || enCurso !== null;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3" aria-busy={ocupado}>
        <button
          type="button"
          onClick={() => void alternar("convocatoria", deFondo)}
          disabled={ocupado}
          className="rounded-full bg-pine px-4 py-2 text-sm font-medium text-ink shadow-sm transition duration-200 hover:-translate-y-0.5 hover:bg-pine-hover disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0"
        >
          {cargando
            ? "Cargando alertas..."
            : enCurso === "convocatoria"
              ? "Guardando..."
              : deFondo
                ? "Dejar de seguir"
                : "Seguir este fondo"}
        </button>

        {institucion ? (
          <button
            type="button"
            onClick={() => void alternar("institucion", deInstitucion)}
            disabled={ocupado}
            className="rounded-full border-2 border-ink bg-paper px-4 py-2 text-sm text-ink transition duration-200 hover:-translate-y-0.5 hover:bg-foam disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0"
          >
            {enCurso === "institucion"
              ? "Guardando..."
              : deInstitucion
                ? `Dejar de seguir ${institucion}`
                : `Seguir convocatorias de ${institucion}`}
          </button>
        ) : null}

        <Link href="/alertas/preferencias" className="text-sm text-pine-text transition hover:underline">
          Configurar alertas
        </Link>
      </div>

      {error ? (
        <p role="alert" className="rounded-2xl border border-clay/30 bg-clay/10 px-4 py-3 text-sm text-ink">
          {error}
        </p>
      ) : null}
    </div>
  );
}
