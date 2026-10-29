import { esResto, formatoNumero, marcasEje, ordenarAnios, porcentaje, type Serie } from "@/lib/analisis";

// Columnas (barras verticales) para distribuciones por año: años de menor a mayor y
// "Sin año"/"Sin fecha" al final, separado. Una sola serie → un color (--serie-1), sin leyenda.
// El valor va arriba de cada columna solo si hay pocas; si no, tooltip + tabla.

interface GraficoColumnasProps {
  titulo: string;
  serie: Serie;
  total?: number;
  nota?: string;
}

const ALTO = 180;
const MAXIMO_CON_VALOR = 12;
const MAXIMO_ETIQUETAS_X = 8;

export default function GraficoColumnas({ titulo, serie, total, nota }: GraficoColumnasProps) {
  const columnas = ordenarAnios(serie);
  const hayDatos = columnas.some((item) => item.cantidad > 0);
  const marcas = marcasEje(Math.max(0, ...columnas.map((item) => item.cantidad)));
  const tope = marcas[marcas.length - 1];
  const conValor = columnas.length <= MAXIMO_CON_VALOR;
  const paso = Math.ceil(columnas.length / MAXIMO_ETIQUETAS_X);

  const detalle = (cantidad: number) =>
    total !== undefined ? `${formatoNumero(cantidad)} (${porcentaje(cantidad, total)})` : formatoNumero(cantidad);
  // Con muchas columnas se etiquetan algunas; el último año y "Sin año" siempre
  const llevaEtiqueta = (indice: number) =>
    conValor || indice % paso === 0 || indice === columnas.length - 1 || esResto(columnas[indice].etiqueta);

  let contenido;
  if (!hayDatos) {
    contenido = <p className="text-sm text-ink/70">No hay datos para estos filtros.</p>;
  } else if (columnas.length === 1) {
    // Una sola columna no se grafica: se muestra el número
    contenido = (
      <p className="text-sm text-ink/80">
        <span className="font-medium text-ink">{columnas[0].etiqueta}</span>:{" "}
        <span className="text-2xl text-ink">{detalle(columnas[0].cantidad)}</span>
      </p>
    );
  } else {
    const mayor = columnas.reduce((a, b) => (b.cantidad > a.cantidad ? b : a));
    // El separador antes de "Sin año" se aplica igual en columnas y etiquetas para que queden alineadas
    const separado = (etiqueta: string, indice: number) =>
      esResto(etiqueta) && indice > 0 && !esResto(columnas[indice - 1].etiqueta) ? "ml-3" : "";

    contenido = (
      <div
        role="img"
        aria-label={`${titulo}: ${columnas.length} columnas, de ${columnas[0].etiqueta} a ${columnas[columnas.length - 1].etiqueta}. El mayor es ${mayor.etiqueta} con ${formatoNumero(mayor.cantidad)}.`}
        className="w-full pt-5 pl-9"
      >
        <div className="relative w-full" style={{ height: ALTO }}>
          {/* Grilla y eje Y: recesivos y sólidos */}
          {marcas.map((marca) => (
            <div key={marca} className="absolute right-0 left-0" style={{ top: ALTO - (marca / tope) * ALTO }}>
              <div className={`border-t ${marca === 0 ? "border-ink/15" : "border-ink/10"}`} />
              <span className="absolute right-full mr-2 -translate-y-1/2 text-xs text-ink/70">{formatoNumero(marca)}</span>
            </div>
          ))}

          <div className="absolute inset-0 flex items-end gap-[2px]">
            {columnas.map((item, indice) => (
              <div
                key={item.etiqueta}
                className={`group relative flex h-full min-w-0 flex-1 flex-col items-center justify-end hover:bg-foam/60 ${separado(item.etiqueta, indice)}`}
              >
                {conValor ? (
                  <span className="mb-0.5 text-xs whitespace-nowrap text-ink">{formatoNumero(item.cantidad)}</span>
                ) : null}
                <div
                  className="entrada-columna w-full max-w-10 rounded-t-[4px] bg-(--serie-1)"
                  style={{
                    height: tope > 0 ? (item.cantidad / tope) * ALTO : 0,
                    animationDelay: `${Math.min(indice * 25, 240)}ms`,
                  }}
                />
                <span
                  aria-hidden="true"
                  className={`pointer-events-none absolute top-0 z-10 -translate-y-full rounded-lg border-2 border-ink bg-paper px-2.5 py-1.5 text-xs whitespace-nowrap text-ink shadow-md tooltip-grafico ${
                    indice === 0 ? "left-0" : indice === columnas.length - 1 ? "right-0" : "left-1/2 -translate-x-1/2"
                  }`}
                >
                  <span className="block font-medium">{item.etiqueta}</span>
                  {detalle(item.cantidad)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Eje X */}
        <div className="mt-1 flex gap-[2px]">
          {columnas.map((item, indice) => (
            <span
              key={item.etiqueta}
              title={item.etiqueta}
              className={`min-w-0 flex-1 overflow-hidden text-center text-xs whitespace-nowrap text-ink/70 ${separado(item.etiqueta, indice)}`}
            >
              {llevaEtiqueta(indice) ? item.etiqueta : ""}
            </span>
          ))}
        </div>
      </div>
    );
  }

  return (
    <figure className="grafico-analisis flex min-w-0 flex-col gap-3 rounded-3xl border-2 border-ink bg-paper p-5">
      <figcaption className="text-base font-medium text-ink">{titulo}</figcaption>
      {contenido}
      {nota ? <p className="text-xs text-ink/70">{nota}</p> : null}
      {hayDatos ? (
        <details className="text-sm text-ink">
          <summary className="inline-flex min-h-9 cursor-pointer items-center rounded-lg text-ink/70 hover:text-ink pointer-coarse:min-h-11">Ver tabla</summary>
          <div className="mt-2 max-w-full overflow-x-auto">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">{titulo}</caption>
              <thead>
                <tr className="border-b border-ink/15 text-ink/70">
                  <th scope="col" className="py-1 pr-3 font-normal">Año</th>
                  <th scope="col" className="py-1 pr-3 text-right font-normal">Cantidad</th>
                  {total !== undefined ? <th scope="col" className="py-1 text-right font-normal">%</th> : null}
                </tr>
              </thead>
              <tbody>
                {columnas.map((item) => (
                  <tr key={item.etiqueta} className="border-b border-ink/10">
                    <th scope="row" className="py-1 pr-3 font-normal">{item.etiqueta}</th>
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
