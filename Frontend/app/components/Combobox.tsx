"use client";

import { KeyboardEvent, useEffect, useId, useMemo, useRef, useState } from "react";

// Combo con autocompletado: se escribe para filtrar las opciones (sin importar
// tildes ni mayúsculas) y se elige con el mouse o con las flechas + Enter.
// Reemplaza a los <select> de la app; con `name` envía el valor en un input oculto.

export type OpcionCombo = string | { valor: string; label: string };

interface ComboboxProps {
  id: string;
  name?: string;
  options: OpcionCombo[];
  value?: string;
  defaultValue?: string;
  onChange?: (valor: string) => void;
  placeholder?: string;
  // Opción que representa "sin filtro" (valor ""), p. ej. "Todos los departamentos"
  opcionVacia?: string;
  required?: boolean;
  invalid?: boolean;
  disabled?: boolean;
  ariaLabel?: string;
  className?: string;
}

const chevron =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='none' stroke='%23102a3c' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M5 7.5 10 12.5 15 7.5'/%3E%3C/svg%3E\")";

export const ESTILO_COMBO =
  "h-11 w-full rounded-xl border-2 border-ink bg-foam/70 bg-[length:16px] bg-[position:right_1rem_center] bg-no-repeat px-4 pr-11 text-sm text-ink outline-none transition placeholder:text-ink/50 focus:border-pine focus:bg-paper disabled:cursor-not-allowed disabled:opacity-60";

const ESTILO_INVALIDO =
  "h-11 w-full rounded-xl border-2 border-red-600 bg-red-50 bg-[length:16px] bg-[position:right_1rem_center] bg-no-repeat px-4 pr-11 text-sm text-ink outline-none transition focus:border-red-600";

function normalizar(texto: string) {
  return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
}

function aOpcion(opcion: OpcionCombo) {
  return typeof opcion === "string" ? { valor: opcion, label: opcion } : opcion;
}

export default function Combobox({
  id,
  name,
  options,
  value,
  defaultValue = "",
  onChange,
  placeholder,
  opcionVacia,
  required = false,
  invalid = false,
  disabled = false,
  ariaLabel,
  className,
}: ComboboxProps) {
  const controlado = value !== undefined;
  const [interno, setInterno] = useState(defaultValue);
  const seleccionado = controlado ? value : interno;

  const opciones = useMemo(() => {
    const lista = options.map(aOpcion);
    return opcionVacia ? [{ valor: "", label: opcionVacia }, ...lista] : lista;
  }, [options, opcionVacia]);

  // Texto que muestra el input para un valor; "" sin opción propia queda vacío
  const textoDe = (valor: string) => opciones.find((opcion) => opcion.valor === valor)?.label ?? valor;

  const [texto, setTexto] = useState(() => textoDe(seleccionado));
  const [abierto, setAbierto] = useState(false);
  const [filtrando, setFiltrando] = useState(false);
  const [activo, setActivo] = useState(0);
  const contenedor = useRef<HTMLDivElement>(null);
  const lista = useRef<HTMLUListElement>(null);
  const listaId = useId();

  // Si el valor o las opciones cambian desde afuera, el texto los acompaña.
  // Se compara por contenido: los padres suelen pasar un array nuevo en cada render.
  const firma = `${seleccionado}\u0000${opciones.map((opcion) => `${opcion.valor}\u0001${opcion.label}`).join("\u0002")}`;
  const [firmaPrevia, setFirmaPrevia] = useState(firma);
  if (firma !== firmaPrevia) {
    setFirmaPrevia(firma);
    if (!filtrando) setTexto(textoDe(seleccionado));
  }

  const visibles = useMemo(() => {
    if (!filtrando || !texto.trim()) return opciones;
    const buscado = normalizar(texto);
    return opciones.filter((opcion) => normalizar(opcion.label).includes(buscado));
  }, [opciones, texto, filtrando]);

  useEffect(() => {
    if (!abierto) return;
    lista.current
      ?.querySelector<HTMLElement>(`[data-indice="${activo}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }, [activo, abierto]);

  function elegir(valor: string) {
    if (valor !== seleccionado) {
      if (!controlado) setInterno(valor);
      onChange?.(valor);
    }
    setTexto(textoDe(valor));
    setFiltrando(false);
    setAbierto(false);
  }

  function abrir() {
    if (disabled) return;
    const indice = visibles.findIndex((opcion) => opcion.valor === seleccionado);
    setActivo(indice >= 0 ? indice : 0);
    setAbierto(true);
  }

  function cerrar() {
    // Lo escrito que no coincide con ninguna opción no queda elegido
    setAbierto(false);
    setFiltrando(false);
    setTexto(textoDe(seleccionado));
  }

  function tecla(evento: KeyboardEvent<HTMLInputElement>) {
    if (evento.key === "ArrowDown") {
      evento.preventDefault();
      if (!abierto) return abrir();
      setActivo((actual) => Math.min(actual + 1, visibles.length - 1));
    } else if (evento.key === "ArrowUp") {
      evento.preventDefault();
      setActivo((actual) => Math.max(actual - 1, 0));
    } else if (evento.key === "Enter") {
      if (abierto && visibles[activo]) {
        evento.preventDefault();
        elegir(visibles[activo].valor);
      }
    } else if (evento.key === "Escape") {
      if (abierto) {
        evento.preventDefault();
        cerrar();
      }
    } else if (evento.key === "Tab") {
      if (abierto && filtrando && visibles.length === 1) elegir(visibles[0].valor);
      else cerrar();
    }
  }

  return (
    <div
      ref={contenedor}
      className={`relative ${className ?? "w-full"}`}
      onBlur={(evento) => {
        if (!contenedor.current?.contains(evento.relatedTarget as Node)) cerrar();
      }}
    >
      <input
        id={id}
        type="text"
        role="combobox"
        autoComplete="off"
        aria-autocomplete="list"
        aria-expanded={abierto}
        aria-controls={listaId}
        aria-activedescendant={abierto && visibles[activo] ? `${listaId}-${activo}` : undefined}
        aria-invalid={invalid || undefined}
        aria-label={ariaLabel}
        required={required}
        disabled={disabled}
        placeholder={placeholder}
        value={texto}
        onChange={(evento) => {
          setTexto(evento.target.value);
          setFiltrando(true);
          setActivo(0);
          setAbierto(true);
        }}
        onFocus={(evento) => evento.target.select()}
        onClick={() => (abierto ? undefined : abrir())}
        onKeyDown={tecla}
        className={invalid ? ESTILO_INVALIDO : ESTILO_COMBO}
        style={{ backgroundImage: chevron }}
      />
      {name ? <input type="hidden" name={name} value={seleccionado} /> : null}

      {abierto ? (
        <ul
          ref={lista}
          id={listaId}
          role="listbox"
          className="absolute z-40 mt-1 max-h-64 w-full overflow-auto rounded-xl border-2 border-ink/60 bg-paper p-1 shadow-lg"
        >
          {visibles.length === 0 ? (
            <li className="px-3 py-2 text-sm text-ink/60">Sin coincidencias</li>
          ) : (
            visibles.map((opcion, indice) => (
              <li
                key={opcion.valor || "__vacia"}
                id={`${listaId}-${indice}`}
                data-indice={indice}
                role="option"
                aria-selected={opcion.valor === seleccionado}
                // mousedown evita que el blur del input cierre la lista antes del click
                onMouseDown={(evento) => {
                  evento.preventDefault();
                  elegir(opcion.valor);
                }}
                onMouseEnter={() => setActivo(indice)}
                className={`cursor-pointer rounded-lg px-3 py-2 text-sm ${
                  indice === activo ? "bg-foam text-ink" : "text-ink/85"
                } ${opcion.valor === seleccionado ? "font-medium text-pine-text" : ""}`}
              >
                {opcion.label}
              </li>
            ))
          )}
        </ul>
      ) : null}
    </div>
  );
}
