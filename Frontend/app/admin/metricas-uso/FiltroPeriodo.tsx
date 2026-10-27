"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition, type FormEvent } from "react";
import DateRangePicker, { type RangoFechas } from "@/app/components/DateRangePicker";

// Rango de fechas de las métricas de uso; va a la URL (?desde&hasta) al aplicar.
// Sin rango, la API usa los últimos 30 días.

interface FiltroPeriodoProps {
  desde: string;
  hasta: string;
}

function hrefMetricas(rango: RangoFechas) {
  const query = new URLSearchParams();
  if (rango.desde) query.set("desde", rango.desde);
  if (rango.hasta) query.set("hasta", rango.hasta);
  const texto = query.toString();
  return texto ? `/admin/metricas-uso?${texto}` : "/admin/metricas-uso";
}

export default function FiltroPeriodo({ desde, hasta }: FiltroPeriodoProps) {
  const router = useRouter();
  const [periodo, setPeriodo] = useState<RangoFechas>({ desde, hasta });
  const [aplicando, startTransition] = useTransition();

  // En una transición: mientras llegan las métricas nuevas, los botones quedan en espera
  function ir(rango: RangoFechas) {
    startTransition(() => router.push(hrefMetricas(rango)));
  }

  function aplicar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    ir(periodo);
  }

  return (
    <form
      onSubmit={aplicar}
      aria-label="Período de las métricas"
      aria-busy={aplicando}
      className="flex flex-wrap items-end gap-3 rounded-3xl border-2 border-ink bg-paper p-5"
    >
      <div className="w-full max-w-sm min-w-0">
        <DateRangePicker id="metricas-periodo" label="Período" value={periodo} onChange={setPeriodo} />
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => ir({ desde: "", hasta: "" })}
          disabled={aplicando}
          className="presionable inline-flex min-h-11 items-center rounded-full border-2 border-ink px-4 text-sm text-ink hover:bg-foam disabled:cursor-wait disabled:opacity-60"
        >
          Últimos 30 días
        </button>
        <button
          type="submit"
          disabled={aplicando}
          className="presionable inline-flex min-h-11 items-center rounded-full border-2 border-ink bg-pine px-5 text-sm font-medium text-ink hover:bg-pine-hover disabled:cursor-wait disabled:opacity-60"
        >
          {aplicando ? "Aplicando…" : "Aplicar"}
        </button>
      </div>
    </form>
  );
}
