"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
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

  function aplicar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    router.push(hrefMetricas(periodo));
  }

  return (
    <form
      onSubmit={aplicar}
      aria-label="Período de las métricas"
      className="flex flex-wrap items-end gap-3 rounded-3xl border-2 border-ink bg-paper p-5"
    >
      <div className="w-full max-w-sm min-w-0">
        <DateRangePicker id="metricas-periodo" label="Período" value={periodo} onChange={setPeriodo} />
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => router.push(hrefMetricas({ desde: "", hasta: "" }))}
          className="rounded-full border-2 border-ink px-4 py-2 text-sm text-ink transition hover:bg-foam"
        >
          Últimos 30 días
        </button>
        <button
          type="submit"
          className="rounded-full border-2 border-ink bg-pine px-5 py-2 text-sm font-medium text-ink transition hover:bg-pine-hover"
        >
          Aplicar
        </button>
      </div>
    </form>
  );
}
