"use client";

import { useState, type MouseEvent } from "react";
import { toast } from "sonner";
import { nombreDeDescarga } from "@/lib/analisis";

// Botones "Exportar CSV/PDF". Siguen siendo <a download> a /analisis-datos/exportar (sin JS
// funcionan igual), pero con JS se descarga por fetch para poder avisar el progreso y,
// sobre todo, mostrar el error de la API en lugar de bajar un archivo con el mensaje adentro.

type Formato = "csv" | "pdf";

interface BotonesExportarProps {
  hrefs: Record<Formato, string>;
}

const FORMATOS: Formato[] = ["csv", "pdf"];

async function descargar(href: string, formato: Formato) {
  let response: Response;
  try {
    response = await fetch(href, { cache: "no-store" });
  } catch {
    throw new Error("No se pudo conectar con el servidor.");
  }
  if (!response.ok) {
    const texto = (await response.text().catch(() => "")).trim().slice(0, 300);
    throw new Error(texto || `No se pudo exportar (${response.status}).`);
  }
  // Con la sesión vencida el proxy redirige al login y el fetch termina en su HTML con 200:
  // no se descarga esa página como si fuera el reporte
  const tipo = response.headers.get("Content-Type") ?? "";
  if (!tipo.includes(formato === "pdf" ? "application/pdf" : "text/csv")) {
    throw new Error("Tu sesión venció. Volvé a iniciar sesión para exportar.");
  }

  const archivo = nombreDeDescarga(response.headers.get("Content-Disposition"), `interfascia.${formato}`);
  const url = URL.createObjectURL(await response.blob());
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = archivo;
  document.body.append(enlace);
  enlace.click();
  enlace.remove();
  // Se libera después: algunos navegadores todavía están leyendo el blob al volver del click
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
  return archivo;
}

export default function BotonesExportar({ hrefs }: BotonesExportarProps) {
  const [enCurso, setEnCurso] = useState<Formato | null>(null);
  const [error, setError] = useState<string | null>(null);

  function exportar(evento: MouseEvent<HTMLAnchorElement>, formato: Formato) {
    evento.preventDefault();
    if (enCurso) return;

    const nombre = formato.toUpperCase();
    setEnCurso(formato);
    setError(null);

    const promesa = descargar(hrefs[formato], formato);
    toast.promise(promesa, {
      loading: `Generando ${nombre}…`,
      success: (archivo) => `${nombre} listo: ${archivo}`,
      error: (excepcion) => (excepcion instanceof Error ? excepcion.message : `No se pudo exportar el ${nombre}.`),
    });
    promesa
      .catch((excepcion) => {
        setError(excepcion instanceof Error ? excepcion.message : `No se pudo exportar el ${nombre}.`);
      })
      .finally(() => setEnCurso(null));
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <div className="flex flex-wrap gap-2" aria-busy={enCurso !== null}>
        {FORMATOS.map((formato) => (
          <a
            key={formato}
            href={hrefs[formato]}
            download
            onClick={(evento) => exportar(evento, formato)}
            aria-disabled={enCurso !== null || undefined}
            className={`presionable inline-flex min-h-10 items-center rounded-full border-2 border-ink bg-paper px-4 text-sm text-ink hover:bg-foam pointer-coarse:min-h-11 ${
              enCurso && enCurso !== formato ? "opacity-60" : ""
            } ${enCurso === formato ? "cursor-progress" : ""}`}
          >
            {/* El texto no cambia (sin saltos de layout): el progreso lo cuenta el aviso */}
            Exportar {formato.toUpperCase()}
          </a>
        ))}
      </div>
      {error ? (
        <p role="alert" className="max-w-sm rounded-2xl border border-clay/30 bg-clay/10 px-3 py-2 text-sm text-ink">
          {error}
        </p>
      ) : null}
    </div>
  );
}
