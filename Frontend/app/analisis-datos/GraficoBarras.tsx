import { anchoBarra, formatoNumero, porcentaje, type Serie } from "@/lib/analisis";

// Barras horizontales para categorías, en el orden que manda la API (de mayor a menor).
// Una sola serie → un solo color (--serie-1) y sin leyenda: el título la nombra.

interface GraficoBarrasProps {
  titulo: string;
  serie: Serie;
  // Si viene, se muestra además el % de cada categoría sobre este total
  total?: number;
  nota?: string;
}

// Más categorías que esto quedan solo en la tabla, para que el gráfico se pueda leer
const MAXIMO_VISIBLES = 12;

export default function GraficoBarras({ titulo, serie, total, nota }: GraficoBarrasProps) {
  const conDatos = serie.filter((item) => item.cantidad > 0);
  const visibles = serie.slice(0, MAXIMO_VISIBLES);
  const ocultas = serie.length - visibles.length;
  const maximo = Math.max(0, ...serie.map((item) => item.cantidad));

  const detalle = (cantidad: number) =>
    total !== undefined ? `${formatoNumero(cantidad)} (${porcentaje(cantidad, total)})` : formatoNumero(cantidad);

  let contenido;
  if (conDatos.length === 0) {
    contenido = <p className="text-sm text-ink/70">No hay datos para estos filtros.</p>;
  } else if (serie.length === 1) {
    // Una sola categoría no se grafica: se muestra el número
    contenido = (
      <p className="text-sm text-ink/80">
        <span className="font-medium text-ink">{serie[0].etiqueta}</span>:{" "}
        <span className="text-2xl text-ink">{detalle(serie[0].cantidad)}</span>
      </p>
    );
  } else {
    const mayor = serie.reduce((a, b) => (b.cantidad > a.cantidad ? b : a));
    contenido = (
      <>
        <div
          role="img"
          aria-label={`${titulo}: ${serie.length} categorías. La mayor es ${mayor.etiqueta} con ${formatoNumero(mayor.cantidad)}.`}
          className="flex flex-col gap-0.5"
        >
          {visibles.map((item, indice) => {
            const ancho = anchoBarra(item.cantidad, maximo);
            return (
              <div
                key={item.etiqueta}
                className="group relative grid grid-cols-1 items-center gap-x-3 rounded-md px-1 py-0.5 hover:bg-foam/60 sm:grid-cols-[minmax(0,13rem)_minmax(0,1fr)]"
              >
                <span className="truncate text-sm text-ink/80" title={item.etiqueta}>
                  {item.etiqueta}
                </span>
                {/* La barra se mide sobre el ancho menos el lugar del valor, que va al final */}
                <div className="relative h-5 w-[calc(100%-4.5rem)]">
                  <div
                    className="entrada-barra absolute top-1/2 left-0 h-3 -translate-y-1/2 rounded-r-[4px] bg-(--serie-1)"
                    // Entrada escalonada corta (tope 240ms) para que se lea como lista
                    style={{ width: `${ancho}%`, animationDelay: `${Math.min(indice * 30, 240)}ms` }}
                  />
                  <span
                    className="absolute top-1/2 ml-1.5 -translate-y-1/2 text-sm whitespace-nowrap text-ink"
                    style={{ left: `${ancho}%` }}
                  >
                    {formatoNumero(item.cantidad)}
                  </span>
                </div>
                <span
                  aria-hidden="true"
                  className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1 max-w-[16rem] -translate-x-1/2 rounded-lg border-2 border-ink bg-paper px-2.5 py-1.5 text-xs text-ink shadow-md tooltip-grafico"
                >
                  <span className="block font-medium break-words">{item.etiqueta}</span>
                  {detalle(item.cantidad)}
                </span>
              </div>
            );
          })}
        </div>
        {ocultas > 0 ? (
          <p className="mt-2 text-xs text-ink/70">
            Se muestran las {MAXIMO_VISIBLES} primeras; las otras {ocultas} están en la tabla.
          </p>
        ) : null}
      </>
    );
  }

  return (
    <figure className="grafico-analisis flex min-w-0 flex-col gap-3 rounded-3xl border-2 border-ink bg-paper p-5">
      <figcaption className="text-base font-medium text-ink">{titulo}</figcaption>
      {contenido}
      {nota ? <p className="text-xs text-ink/70">{nota}</p> : null}
      {conDatos.length > 0 ? (
        <details className="text-sm text-ink">
          <summary className="inline-flex min-h-9 cursor-pointer items-center rounded-lg text-ink/70 hover:text-ink pointer-coarse:min-h-11">Ver tabla</summary>
          <div className="mt-2 max-w-full overflow-x-auto">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">{titulo}</caption>
              <thead>
                <tr className="border-b border-ink/15 text-ink/70">
                  <th scope="col" className="py-1 pr-3 font-normal">Categoría</th>
                  <th scope="col" className="py-1 pr-3 text-right font-normal">Cantidad</th>
                  {total !== undefined ? <th scope="col" className="py-1 text-right font-normal">%</th> : null}
                </tr>
              </thead>
              <tbody>
                {serie.map((item) => (
                  <tr key={item.etiqueta} className="border-b border-ink/10">
                    <th scope="row" className="py-1 pr-3 font-normal break-words">{item.etiqueta}</th>
                    <td className="py-1 pr-3 text-right tabular-nums">{formatoNumero(item.cantidad)}</td>
                    {total !== undefined ? (
                      <td className="py-1 text-right tabular-nums">{porcentaje(item.cantidad, total)}</td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      ) : null}
    </figure>
  );
}
