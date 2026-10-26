"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import Combobox, { ESTILO_COMBO } from "@/app/components/Combobox";
import DateRangePicker, { formatoCorto, type RangoFechas } from "@/app/components/DateRangePicker";
import { ESTADOS, etiquetaFiltro, hrefAnalisis, type Filtros, type OpcionesAnalisis } from "@/lib/analisis";

// Fila única de filtros arriba de los gráficos. Se aplican con "Aplicar" (van a la URL,
// así se pueden compartir) y conservan la vista y la agrupación elegidas.
// La página lo monta con una key por filtros: al cambiar la URL vuelve a leer los valores.

interface FiltrosAnaliticosProps {
  filtros: Filtros;
  opciones: OpcionesAnalisis | null;
}

const MOTIVO_SECTOR = "La plataforma todavía no registra el sector económico de los fondos.";

export default function FiltrosAnaliticos({ filtros, opciones }: FiltrosAnaliticosProps) {
  const router = useRouter();
  const [organismo, setOrganismo] = useState(filtros.organismo);
  const [tematica, setTematica] = useState(filtros.tematica);
  const [estado, setEstado] = useState(filtros.estado);
  const [periodo, setPeriodo] = useState<RangoFechas>({ desde: filtros.desde, hasta: filtros.hasta });

  const estados = opciones?.estados.length ? opciones.estados : ESTADOS;
  const motivoSector = opciones?.sector_economico.motivo || MOTIVO_SECTOR;

  function aplicar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    router.push(hrefAnalisis(filtros, { organismo, tematica, estado, desde: periodo.desde, hasta: periodo.hasta }));
  }

  function limpiar() {
    router.push(hrefAnalisis(filtros, { organismo: "", tematica: "", estado: "", desde: "", hasta: "" }));
  }

  // Chips de lo que está aplicado hoy (lo de la URL, no lo que se está editando)
  const chips: { clave: string; texto: string; sin: Partial<Filtros> }[] = [];
  if (filtros.organismo) chips.push({ clave: "organismo", texto: filtros.organismo, sin: { organismo: "" } });
  if (filtros.tematica) chips.push({ clave: "tematica", texto: filtros.tematica, sin: { tematica: "" } });
  if (filtros.estado) chips.push({ clave: "estado", texto: filtros.estado, sin: { estado: "" } });
  if (filtros.desde || filtros.hasta) {
    const texto =
      filtros.desde && filtros.hasta
        ? `${formatoCorto(filtros.desde)} – ${formatoCorto(filtros.hasta)}`
        : filtros.desde
          ? `desde ${formatoCorto(filtros.desde)}`
          : `hasta ${formatoCorto(filtros.hasta)}`;
    chips.push({ clave: "periodo", texto, sin: { desde: "", hasta: "" } });
  }

  return (
    <form
      onSubmit={aplicar}
      aria-label="Filtros del análisis"
      className="flex flex-col gap-4 rounded-3xl border-2 border-ink bg-paper p-5"
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <div className="flex min-w-0 flex-col gap-1.5">
          <label htmlFor="filtro-organismo" className="text-sm text-ink">Organismo</label>
          <Combobox
            id="filtro-organismo"
            options={opciones?.organismos ?? []}
            value={organismo}
            onChange={setOrganismo}
            opcionVacia="Todos los organismos"
          />
        </div>

        <div className="flex min-w-0 flex-col gap-1.5">
          <label htmlFor="filtro-tematica" className="text-sm text-ink">Área temática</label>
          <Combobox
            id="filtro-tematica"
            options={opciones?.tematicas ?? []}
            value={tematica}
            onChange={setTematica}
            opcionVacia="Todas las áreas"
          />
        </div>

        <div className="flex min-w-0 flex-col gap-1.5">
          <label htmlFor="filtro-estado" className="text-sm text-ink">Estado de convocatoria</label>
          <Combobox
            id="filtro-estado"
            options={estados}
            value={estado}
            onChange={setEstado}
            opcionVacia="Todos los estados"
          />
        </div>

        <div className="min-w-0">
          <DateRangePicker id="filtro-periodo" label="Período" value={periodo} onChange={setPeriodo} />
        </div>

        <div className="flex min-w-0 flex-col gap-1.5">
          <label htmlFor="filtro-sector" className="text-sm text-ink">Sector económico</label>
          <input
            id="filtro-sector"
            type="text"
            disabled
            value="No disponible"
            aria-describedby="filtro-sector-ayuda"
            className={ESTILO_COMBO}
            readOnly
          />
          <p id="filtro-sector-ayuda" className="text-xs text-ink/60">{motivoSector}</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <ul className="flex flex-wrap gap-2" aria-label="Filtros aplicados">
          {chips.length === 0 ? (
            <li className="text-sm text-ink/60">Sin filtros: se muestran todos los datos.</li>
          ) : (
            chips.map((chip) => (
              <li key={chip.clave}>
                <Link
                  href={hrefAnalisis(filtros, chip.sin)}
                  aria-label={`Quitar filtro ${etiquetaFiltro(chip.clave)}: ${chip.texto}`}
                  className="flex max-w-[20rem] items-center gap-2 rounded-full border-2 border-ink bg-foam px-3 py-1 text-sm text-ink transition hover:bg-foam/50"
                >
                  <span className="truncate" title={chip.texto}>
                    <span className="text-ink/70">{etiquetaFiltro(chip.clave)}:</span> {chip.texto}
                  </span>
                  <span aria-hidden="true" className="text-base leading-none">×</span>
                </Link>
              </li>
            ))
          )}
        </ul>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={limpiar}
            className="rounded-full border-2 border-ink px-4 py-2 text-sm text-ink transition hover:bg-foam"
          >
            Limpiar
          </button>
          <button
            type="submit"
            className="rounded-full border-2 border-ink bg-pine px-5 py-2 text-sm font-medium text-ink transition hover:bg-pine-hover"
          >
            Aplicar
          </button>
        </div>
      </div>
    </form>
  );
}
