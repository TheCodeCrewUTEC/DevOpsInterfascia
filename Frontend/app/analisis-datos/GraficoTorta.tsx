"use client";

import { useState } from "react";
import {
  MAXIMO_PORCIONES,
  agruparOtros,
  arcosTorta,
  caminoArco,
  colorCategoria,
  formatoNumero,
  porcentaje,
  restoAlFinal,
  type Serie,
} from "@/lib/analisis";
import GraficoBarras from "./GraficoBarras";

// Torta tipo dona para parte-de-un-todo, con el total en el centro.
// - 3 a 6 porciones. Con más de 6 quedan las 5 primeras + "Otros" (suma del resto);
//   con agrupar={false} cae a barras horizontales.
// - Con 1 o 2 categorías no hay torta: GraficoBarras muestra el número o las dos barras.
// - Colores por posición fija (conocidas o serie), nunca por valor; "Otros"/"Sin …" en gris y al final.
// - La leyenda con texto es obligatoria (hay colores con poco contraste) y además sirve de foco
//   con teclado: al pasar o enfocar una porción, el centro muestra su etiqueta, valor y %.

interface GraficoTortaProps {
  titulo: string;
  serie: Serie;
  nota?: string;
  // Orden fijo de categorías para que cada una conserve su color entre filtros
  conocidas?: readonly string[];
  agrupar?: boolean;
}

const LADO = 200;
const CENTRO = LADO / 2;
const R_EXT = 98;
const R_INT = 62;
// Porciones más chicas que esto no llevan etiqueta directa (solo leyenda)
const MINIMO_ETIQUETA = 8;

export default function GraficoTorta({ titulo, serie, nota, conocidas, agrupar = true }: GraficoTortaProps) {
  const [activa, setActiva] = useState<number | null>(null);

  const positivas = serie.filter((item) => item.cantidad > 0);
  const porciones = agrupar ? agruparOtros(positivas) : restoAlFinal(positivas);
  const total = positivas.reduce((suma, item) => suma + item.cantidad, 0);

  if (porciones.length < 3 || porciones.length > MAXIMO_PORCIONES) {
    return <GraficoBarras titulo={titulo} serie={restoAlFinal(serie)} total={total} nota={nota} />;
  }

  const arcos = arcosTorta(porciones);
  const colores = arcos.map((arco, indice) => colorCategoria(arco.etiqueta, indice, conocidas));
  const seleccion = activa !== null ? arcos[activa] : null;
  const resumen = arcos.map((arco) => `${arco.etiqueta} ${porcentaje(arco.cantidad, total)}`).join(", ");

  return (
    <figure className="grafico-analisis flex min-w-0 flex-col gap-3 rounded-3xl border-2 border-ink bg-paper p-5">
      <figcaption className="text-base font-medium text-ink">{titulo}</figcaption>

      <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-center">
        <div className="relative aspect-square w-full max-w-[13rem] shrink-0">
          <svg
            role="img"
            aria-label={`${titulo}: total ${formatoNumero(total)}. ${resumen}.`}
            viewBox={`0 0 ${LADO} ${LADO}`}
            className="entrada-torta h-full w-full"
            onMouseLeave={() => setActiva(null)}
          >
            {arcos.map((arco, indice) => (
              <path
                key={arco.etiqueta}
                d={caminoArco(CENTRO, CENTRO, R_EXT, R_INT, arco.inicio, arco.fin)}
                fill={colores[indice]}
                fillRule="evenodd"
                // Separación de 2px con el color de la superficie, sin bordes oscuros
                stroke="var(--color-paper, #fff)"
                strokeWidth={2}
                strokeLinejoin="round"
                onMouseEnter={() => setActiva(indice)}
                className={`cursor-default transition-opacity ${activa !== null && activa !== indice ? "opacity-45" : ""}`}
              >
                <title>{`${arco.etiqueta}: ${formatoNumero(arco.cantidad)} (${porcentaje(arco.cantidad, total)})`}</title>
              </path>
            ))}

            {/* Etiqueta directa del % solo en porciones que la dejan entrar; texto ink con halo blanco */}
            {arcos.map((arco) => {
              if (arco.porcentaje < MINIMO_ETIQUETA) return null;
              const medio = (arco.inicio + arco.fin) / 2;
              const radio = (R_EXT + R_INT) / 2;
              return (
                <text
                  key={`texto-${arco.etiqueta}`}
                  x={CENTRO + radio * Math.cos(medio)}
                  y={CENTRO + radio * Math.sin(medio)}
                  textAnchor="middle"
                  dominantBaseline="central"
                  className="pointer-events-none fill-ink text-[11px] font-medium"
                  stroke="var(--color-paper, #fff)"
                  strokeWidth={3}
                  paintOrder="stroke"
                  aria-hidden="true"
                >
                  {porcentaje(arco.cantidad, total)}
                </text>
              );
            })}
          </svg>

          {/* Centro de la dona: el total, o la porción señalada (hace de tooltip) */}
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-[31%] flex flex-col items-center justify-center text-center text-ink"
          >
            {seleccion ? (
              <>
                <span className="line-clamp-2 text-xs leading-tight break-words">{seleccion.etiqueta}</span>
                <span className="text-lg leading-tight font-medium">{formatoNumero(seleccion.cantidad)}</span>
                <span className="text-xs text-ink/70">{porcentaje(seleccion.cantidad, total)}</span>
              </>
            ) : (
              <>
                <span className="text-xs text-ink/70">Total</span>
                <span className="text-2xl leading-tight font-medium">{formatoNumero(total)}</span>
              </>
            )}
          </div>
        </div>

        <ul className="flex w-full min-w-0 flex-1 flex-col gap-1" aria-label={`Leyenda de ${titulo}`}>
          {arcos.map((arco, indice) => (
            <li key={arco.etiqueta}>
              <button
                type="button"
                onMouseEnter={() => setActiva(indice)}
                onMouseLeave={() => setActiva(null)}
                onFocus={() => setActiva(indice)}
                onBlur={() => setActiva(null)}
                className={`flex min-h-9 w-full min-w-0 items-center gap-2 rounded-lg px-2 py-1 text-left text-sm text-ink transition-colors pointer-coarse:min-h-11 ${
                  activa === indice ? "bg-foam" : "hover:bg-foam/60"
                }`}
              >
                <span aria-hidden="true" className="h-3 w-3 shrink-0 rounded-sm" style={{ backgroundColor: colores[indice] }} />
                <span className="min-w-0 flex-1 truncate" title={arco.etiqueta}>
                  {arco.etiqueta}
                </span>
                <span className="shrink-0 tabular-nums">{formatoNumero(arco.cantidad)}</span>
                <span className="w-12 shrink-0 text-right text-ink/70 tabular-nums">{porcentaje(arco.cantidad, total)}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>

      {nota ? <p className="text-xs text-ink/70">{nota}</p> : null}

      <details className="text-sm text-ink">
        <summary className="inline-flex min-h-9 cursor-pointer items-center rounded-lg text-ink/70 hover:text-ink pointer-coarse:min-h-11">Ver tabla</summary>
        <div className="mt-2 max-w-full overflow-x-auto">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">{titulo}</caption>
            <thead>
              <tr className="border-b border-ink/15 text-ink/70">
                <th scope="col" className="py-1 pr-3 font-normal">Categoría</th>
                <th scope="col" className="py-1 pr-3 text-right font-normal">Cantidad</th>
                <th scope="col" className="py-1 text-right font-normal">%</th>
              </tr>
            </thead>
            <tbody>
              {/* La tabla lleva todas las categorías, también las que la torta sumó en "Otros" */}
              {restoAlFinal(positivas).map((item) => (
                <tr key={item.etiqueta} className="border-b border-ink/10">
                  <th scope="row" className="py-1 pr-3 font-normal break-words">{item.etiqueta}</th>
                  <td className="py-1 pr-3 text-right tabular-nums">{formatoNumero(item.cantidad)}</td>
                  <td className="py-1 text-right tabular-nums">{porcentaje(item.cantidad, total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}
