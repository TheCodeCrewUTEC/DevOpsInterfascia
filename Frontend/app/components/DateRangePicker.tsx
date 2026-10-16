"use client";

import { useEffect, useRef, useState } from "react";

// Selector de rango: el primer click marca "desde", el segundo "hasta".
// Las fechas viajan como texto ISO (AAAA-MM-DD), igual que las espera la API.

export type RangoFechas = { desde: string; hasta: string };

interface DateRangePickerProps {
  id: string;
  label: string;
  value: RangoFechas;
  onChange: (rango: RangoFechas) => void;
}

const MESES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];
const DIAS = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"];

function aIso(fecha: Date) {
  const mes = String(fecha.getMonth() + 1).padStart(2, "0");
  const dia = String(fecha.getDate()).padStart(2, "0");
  return `${fecha.getFullYear()}-${mes}-${dia}`;
}

function desdeIso(iso: string) {
  const [anio, mes, dia] = iso.split("-").map(Number);
  return new Date(anio, mes - 1, dia);
}

export function formatoCorto(iso: string) {
  if (!iso) return "";
  const [anio, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${anio}`;
}

// Días del mes en semanas que empiezan el lunes; null = casillero vacío
function semanasDe(anio: number, mes: number) {
  const primero = new Date(anio, mes, 1);
  const vacios = (primero.getDay() + 6) % 7;
  const total = new Date(anio, mes + 1, 0).getDate();
  const dias: (Date | null)[] = Array.from({ length: vacios }, () => null);
  for (let dia = 1; dia <= total; dia++) dias.push(new Date(anio, mes, dia));
  while (dias.length % 7 !== 0) dias.push(null);
  return dias;
}

export default function DateRangePicker({ id, label, value, onChange }: DateRangePickerProps) {
  const [abierto, setAbierto] = useState(false);
  const [mes, setMes] = useState(() => {
    const base = value.desde ? desdeIso(value.desde) : new Date();
    return new Date(base.getFullYear(), base.getMonth(), 1);
  });
  const [borrador, setBorrador] = useState<RangoFechas>(value);
  const [hover, setHover] = useState<string | null>(null);
  const contenedor = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!abierto) return;

    function clickAfuera(evento: MouseEvent) {
      if (!contenedor.current?.contains(evento.target as Node)) setAbierto(false);
    }
    function tecla(evento: KeyboardEvent) {
      if (evento.key === "Escape") setAbierto(false);
    }

    document.addEventListener("mousedown", clickAfuera);
    document.addEventListener("keydown", tecla);
    return () => {
      document.removeEventListener("mousedown", clickAfuera);
      document.removeEventListener("keydown", tecla);
    };
  }, [abierto]);

  function abrir() {
    setBorrador(value);
    setAbierto((actual) => !actual);
  }

  function elegirDia(iso: string) {
    // Sin desde, o con el rango ya completo: se empieza uno nuevo
    if (!borrador.desde || borrador.hasta) {
      setBorrador({ desde: iso, hasta: "" });
      return;
    }

    const rango = iso < borrador.desde ? { desde: iso, hasta: borrador.desde } : { desde: borrador.desde, hasta: iso };
    setBorrador(rango);
    onChange(rango);
    setAbierto(false);
  }

  function limpiar() {
    const vacio = { desde: "", hasta: "" };
    setBorrador(vacio);
    onChange(vacio);
    setAbierto(false);
  }

  function moverMes(delta: number) {
    setMes((actual) => new Date(actual.getFullYear(), actual.getMonth() + delta, 1));
  }

  const hasta = borrador.hasta || (borrador.desde && hover && hover > borrador.desde ? hover : "");
  const hoy = aIso(new Date());
  const resumen =
    value.desde && value.hasta
      ? `${formatoCorto(value.desde)} – ${formatoCorto(value.hasta)}`
      : "Cualquier fecha";

  return (
    <div ref={contenedor} className="relative flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm text-ink">
        {label}
      </label>
      <div className="flex gap-2">
        <button
          id={id}
          type="button"
          aria-haspopup="dialog"
          aria-expanded={abierto}
          onClick={abrir}
          className="flex h-11 w-full items-center justify-between gap-3 rounded-xl border-2 border-ink bg-foam/70 px-4 text-left text-sm text-ink outline-none transition hover:border-pine focus:border-pine focus:bg-paper"
        >
          <span className={value.desde ? "" : "text-ink/60"}>{resumen}</span>
          <Calendario />
        </button>
        {value.desde ? (
          <button
            type="button"
            onClick={limpiar}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-clay/40 text-lg text-clay transition hover:bg-clay/10"
            aria-label="Quitar filtro de fechas"
          >
            ×
          </button>
        ) : null}
      </div>

      {abierto ? (
        <div
          role="dialog"
          aria-label={label}
          className="absolute top-full left-0 z-40 mt-2 w-full min-w-72 max-w-sm rounded-2xl border-2 border-ink/60 bg-paper p-4 shadow-xl"
        >
          <div className="flex items-center justify-between">
            <button type="button" onClick={() => moverMes(-1)} className="h-8 w-8 rounded-full text-ink transition hover:bg-foam" aria-label="Mes anterior">
              ‹
            </button>
            <p className="text-sm font-medium text-ink" aria-live="polite">
              {MESES[mes.getMonth()]} {mes.getFullYear()}
            </p>
            <button type="button" onClick={() => moverMes(1)} className="h-8 w-8 rounded-full text-ink transition hover:bg-foam" aria-label="Mes siguiente">
              ›
            </button>
          </div>

          <div className="mt-3 grid grid-cols-7 gap-y-1 text-center text-xs text-ink/55">
            {DIAS.map((dia) => (
              <span key={dia} aria-hidden="true">{dia}</span>
            ))}
          </div>

          <div className="mt-1 grid grid-cols-7 gap-y-1" onMouseLeave={() => setHover(null)}>
            {semanasDe(mes.getFullYear(), mes.getMonth()).map((fecha, indice) => {
              if (!fecha) return <span key={`vacio-${indice}`} />;

              const iso = aIso(fecha);
              const extremo = iso === borrador.desde || iso === hasta;
              const dentro = Boolean(borrador.desde && hasta && iso > borrador.desde && iso < hasta);

              return (
                <button
                  key={iso}
                  type="button"
                  onClick={() => elegirDia(iso)}
                  onMouseEnter={() => setHover(iso)}
                  aria-pressed={extremo}
                  aria-label={formatoCorto(iso)}
                  className={`h-9 text-sm transition ${
                    extremo
                      ? "rounded-full bg-pine font-medium text-ink"
                      : dentro
                        ? "bg-foam text-ink"
                        : "rounded-full text-ink/85 hover:bg-foam"
                  } ${iso === hoy && !extremo ? "font-semibold text-pine-text" : ""}`}
                >
                  {fecha.getDate()}
                </button>
              );
            })}
          </div>

          <div className="mt-3 flex items-center justify-between border-t border-ink/10 pt-3">
            <p className="text-xs text-ink/60">
              {borrador.desde && !borrador.hasta ? "Elegí la fecha final" : "Elegí la fecha inicial"}
            </p>
            <button type="button" onClick={limpiar} className="text-xs text-ink/60 underline-offset-2 hover:text-clay hover:underline">
              Limpiar
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Calendario() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true" className="shrink-0 text-ink/70">
      <rect x="3.5" y="5" width="17" height="15" rx="2.5" />
      <path d="M3.5 10h17M8 3v4M16 3v4" />
    </svg>
  );
}
