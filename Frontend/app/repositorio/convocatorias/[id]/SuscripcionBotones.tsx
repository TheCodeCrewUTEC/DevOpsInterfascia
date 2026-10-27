"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";
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
  const router = useRouter();
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
        toast.success(
          tipo === "convocatoria"
            ? "Dejaste de seguir este fondo."
            : `Dejaste de seguir las convocatorias de ${institucion}.`,
        );
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
        toast.success(
          tipo === "convocatoria"
            ? "Ahora seguís este fondo. Te vamos a avisar de sus cambios."
            : `Ahora seguís las convocatorias de ${institucion}.`,
          { action: { label: "Configurar", onClick: () => router.push("/alertas/preferencias") } },
        );
      }
    } catch (err) {
      const mensaje = err instanceof Error ? err.message : "";
      const texto = mensaje && mensaje !== "Failed to fetch" ? mensaje : "No se pudo conectar con el backend.";
      // El error queda en pantalla (role="alert") y además como aviso
      setError(texto);
      toast.error(texto);
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
          className="presionable inline-flex min-h-11 items-center rounded-full bg-pine px-4 text-sm font-medium text-ink shadow-sm hover:bg-pine-hover disabled:cursor-not-allowed disabled:opacity-60"
        >
          {cargando
            ? "Cargando alertas…"
            : enCurso === "convocatoria"
              ? "Guardando…"
              : deFondo
                ? "Dejar de seguir"
                : "Seguir este fondo"}
        </button>

        {institucion ? (
          <button
            type="button"
            onClick={() => void alternar("institucion", deInstitucion)}
            disabled={ocupado}
            className="presionable inline-flex min-h-11 max-w-full items-center rounded-full border-2 border-ink bg-paper px-4 text-left text-sm text-ink hover:bg-foam disabled:cursor-not-allowed disabled:opacity-60"
          >
            {enCurso === "institucion"
              ? "Guardando…"
              : deInstitucion
                ? `Dejar de seguir ${institucion}`
                : `Seguir convocatorias de ${institucion}`}
          </button>
        ) : null}

        <Link
          href="/alertas/preferencias"
          className="inline-flex min-h-11 items-center text-sm text-pine-text underline-offset-4 hover:underline"
        >
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
