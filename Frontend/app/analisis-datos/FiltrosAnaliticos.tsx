"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition, type FormEvent } from "react";
import Combobox, { ESTILO_COMBO } from "@/app/components/Combobox";
import DateRangePicker, { formatoCorto, type RangoFechas } from "@/app/components/DateRangePicker";
import PanelInferior from "@/app/components/PanelInferior";
import { ESTADOS, etiquetaFiltro, hrefAnalisis, type Filtros, type OpcionesAnalisis } from "@/lib/analisis";

// Filtros del análisis. En desktop: una fila arriba de los gráficos. En mobile (< md): un botón
// "Filtros (n)" que abre los mismos campos en un panel desde abajo (Vaul).
// Se aplican con "Aplicar" (van a la URL, así se pueden compartir) y conservan la vista y la agrupación.
// La página lo monta con una key por filtros: al cambiar la URL vuelve a leer los valores.

interface FiltrosAnaliticosProps {
  filtros: Filtros;
  opciones: OpcionesAnalisis | null;
}

const MOTIVO_SECTOR = "La plataforma todavía no registra el sector económico de los fondos.";

const BOTON_SECUNDARIO =
  "presionable inline-flex min-h-10 items-center justify-center rounded-full border-2 border-ink px-4 text-sm text-ink hover:bg-foam disabled:cursor-wait disabled:opacity-60 pointer-coarse:min-h-11";
const BOTON_PRIMARIO =
  "presionable inline-flex min-h-10 items-center justify-center rounded-full border-2 border-ink bg-pine px-5 text-sm font-medium text-ink hover:bg-pine-hover disabled:cursor-wait disabled:opacity-60 pointer-coarse:min-h-11";

export default function FiltrosAnaliticos({ filtros, opciones }: FiltrosAnaliticosProps) {
  const router = useRouter();
  const [aplicando, startTransition] = useTransition();
  const [panelAbierto, setPanelAbierto] = useState(false);
  const [organismo, setOrganismo] = useState(filtros.organismo);
  const [tematica, setTematica] = useState(filtros.tematica);
  const [estado, setEstado] = useState(filtros.estado);
  const [periodo, setPeriodo] = useState<RangoFechas>({ desde: filtros.desde, hasta: filtros.hasta });

  const estados = opciones?.estados.length ? opciones.estados : ESTADOS;
  const motivoSector = opciones?.sector_economico.motivo || MOTIVO_SECTOR;

  // La navegación va en una transición: mientras carga la vista nueva, los botones lo muestran
  function ir(href: string) {
    setPanelAbierto(false);
    startTransition(() => router.push(href));
  }

  function aplicar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    ir(hrefAnalisis(filtros, { organismo, tematica, estado, desde: periodo.desde, hasta: periodo.hasta }));
  }

  function limpiar() {
    ir(hrefAnalisis(filtros, { organismo: "", tematica: "", estado: "", desde: "", hasta: "" }));
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

  // Los campos se dibujan en la fila (desktop) y en el panel (mobile): el prefijo evita ids repetidos
  function campos(prefijo: string) {
    return (
      <>
        <div className="flex min-w-0 flex-col gap-1.5">
          <label htmlFor={`${prefijo}-organismo`} className="text-sm text-ink">Organismo</label>
          <Combobox
            id={`${prefijo}-organismo`}
            options={opciones?.organismos ?? []}
            value={organismo}
            onChange={setOrganismo}
            opcionVacia="Todos los organismos"
          />
        </div>

        <div className="flex min-w-0 flex-col gap-1.5">
          <label htmlFor={`${prefijo}-tematica`} className="text-sm text-ink">Área temática</label>
          <Combobox
            id={`${prefijo}-tematica`}
            options={opciones?.tematicas ?? []}
            value={tematica}
            onChange={setTematica}
            opcionVacia="Todas las áreas"
          />
        </div>

        <div className="flex min-w-0 flex-col gap-1.5">
          <label htmlFor={`${prefijo}-estado`} className="text-sm text-ink">Estado de convocatoria</label>
          <Combobox
            id={`${prefijo}-estado`}
            options={estados}
            value={estado}
            onChange={setEstado}
            opcionVacia="Todos los estados"
          />
        </div>

        <div className="min-w-0">
          <DateRangePicker id={`${prefijo}-periodo`} label="Período" value={periodo} onChange={setPeriodo} />
        </div>

        <div className="flex min-w-0 flex-col gap-1.5">
          <label htmlFor={`${prefijo}-sector`} className="text-sm text-ink">Sector económico</label>
          <input
            id={`${prefijo}-sector`}
            type="text"
            disabled
            value="No disponible"
            aria-describedby={`${prefijo}-sector-ayuda`}
            className={ESTILO_COMBO}
            readOnly
          />
          <p id={`${prefijo}-sector-ayuda`} className="text-xs text-ink/70">{motivoSector}</p>
        </div>
      </>
    );
  }

  const botones = (
    <div className="flex gap-2">
      <button type="button" onClick={limpiar} disabled={aplicando} className={BOTON_SECUNDARIO}>
        Limpiar
      </button>
      <button type="submit" disabled={aplicando} className={BOTON_PRIMARIO}>
        {/* Ancho fijo por el texto más largo: el cambio de texto no mueve nada */}
        <span className="grid text-center">
          <span className={`col-start-1 row-start-1 ${aplicando ? "invisible" : ""}`}>Aplicar</span>
          <span aria-hidden={!aplicando} className={`col-start-1 row-start-1 ${aplicando ? "" : "invisible"}`}>
            Aplicando…
          </span>
        </span>
      </button>
    </div>
  );

  const listaChips = (
    <ul className="flex min-w-0 flex-wrap gap-2" aria-label="Filtros aplicados">
      {chips.length === 0 ? (
        <li className="text-sm text-ink/70">Sin filtros: se muestran todos los datos.</li>
      ) : (
        chips.map((chip) => (
          <li key={chip.clave} className="min-w-0">
            <Link
              href={hrefAnalisis(filtros, chip.sin)}
              aria-label={`Quitar filtro ${etiquetaFiltro(chip.clave)}: ${chip.texto}`}
              className="presionable flex min-h-9 max-w-[20rem] items-center gap-2 rounded-full border-2 border-ink bg-foam py-1 pr-2 pl-3 text-sm text-ink hover:bg-paper pointer-coarse:min-h-11"
            >
              <span className="truncate" title={chip.texto}>
                <span className="text-ink/70">{etiquetaFiltro(chip.clave)}:</span> {chip.texto}
              </span>
              <IconoCerrar />
            </Link>
          </li>
        ))
      )}
    </ul>
  );

  return (
    <div aria-busy={aplicando}>
      {/* Desktop: una fila */}
      <form
        onSubmit={aplicar}
        aria-label="Filtros del análisis"
        className="hidden flex-col gap-4 rounded-3xl border-2 border-ink bg-paper p-5 md:flex"
      >
        <div className="grid grid-cols-2 gap-4 xl:grid-cols-5">{campos("filtro")}</div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          {listaChips}
          {botones}
        </div>
      </form>

      {/* Mobile: botón con la cantidad de filtros activos y panel desde abajo */}
      <div className="flex flex-col gap-3 md:hidden">
        <PanelInferior
          abierto={panelAbierto}
          onAbiertoChange={setPanelAbierto}
          titulo="Filtros del análisis"
          descripcion="Se aplican a todas las secciones que los admiten."
          disparador={
            <button type="button" className={`${BOTON_SECUNDARIO} w-full gap-2 bg-paper`}>
              <IconoFiltros />
              Filtros{chips.length > 0 ? ` (${chips.length})` : ""}
            </button>
          }
        >
          <form onSubmit={aplicar} aria-label="Filtros del análisis" className="flex flex-col gap-4">
            {campos("panel")}
            {/* Acciones siempre a mano al pie del panel */}
            <div className="sticky bottom-0 -mx-5 flex justify-end border-t border-ink/10 bg-paper px-5 pt-3 pb-1">
              {botones}
            </div>
          </form>
        </PanelInferior>
        {chips.length > 0 ? listaChips : null}
      </div>
    </div>
  );
}

function IconoCerrar() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true" className="shrink-0 text-ink/70">
      <path d="M4.5 4.5l7 7M11.5 4.5l-7 7" />
    </svg>
  );
}

function IconoFiltros() {
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true" className="shrink-0">
      <path d="M3 5.5h14M5.5 10h9M8 14.5h4" />
    </svg>
  );
}
