import {
  coordenadasLinea,
  etiquetaPeriodo,
  formatoNumero,
  marcasEje,
  puntosLinea,
  type PuntoTiempo,
} from "@/lib/analisis";

// Evolución en el tiempo: una o dos series sobre el MISMO eje Y.
// Colores fijos por orden (--serie-1, --serie-2). Con dos series hay leyenda y,
// en los dos casos, etiqueta directa con el último valor de cada línea.
// El eje X es fluido (en %) y el Y tiene alto fijo en px, así el texto no se achica en mobile.

export type SerieLinea = { nombre: string; puntos: PuntoTiempo[] };

interface GraficoLineasProps {
  titulo: string;
  series: SerieLinea[];
  nota?: string;
}

const ALTO = 220;
const COLORES = ["bg-(--serie-1)", "bg-(--serie-2)"];
const TRAZOS = ["var(--serie-1)", "var(--serie-2)"];
const MAXIMO_ETIQUETAS_X = 6;
const SEPARACION_ETIQUETAS = 16;

// Índices del eje X que llevan etiqueta: el primero, el último y algunos intermedios
function indicesEtiquetados(cantidad: number) {
  const paso = Math.ceil(cantidad / MAXIMO_ETIQUETAS_X);
  const indices: number[] = [];
  for (let indice = 0; indice < cantidad; indice += paso) indices.push(indice);
  const ultimo = cantidad - 1;
  if (indices[indices.length - 1] !== ultimo) {
    // Si el último intermedio queda pegado al final, se saca para que no se pisen
    if (ultimo - indices[indices.length - 1] < paso / 2) indices.pop();
    indices.push(ultimo);
  }
  return indices;
}

export default function GraficoLineas({ titulo, series, nota }: GraficoLineasProps) {
  const visibles = series.slice(0, 2);
  const periodos = Array.from(new Set(visibles.flatMap((serie) => serie.puntos.map((punto) => punto.periodo)))).sort();

  // Cada serie alineada a todos los períodos (sin dato = 0)
  const valores = visibles.map((serie) => {
    const porPeriodo = new Map(serie.puntos.map((punto) => [punto.periodo, punto.cantidad]));
    return periodos.map((periodo) => porPeriodo.get(periodo) ?? 0);
  });
  const hayDatos = valores.some((lista) => lista.some((valor) => valor > 0));
  const marcas = marcasEje(Math.max(0, ...valores.flat()));
  const tope = marcas[marcas.length - 1];
  const dosSeries = visibles.length > 1;

  let contenido;
  if (!hayDatos) {
    contenido = <p className="text-sm text-ink/70">No hay datos para estos filtros.</p>;
  } else if (periodos.length === 1) {
    // Un solo período no es una evolución: se muestran los números
    contenido = (
      <ul className="flex flex-col gap-1 text-sm text-ink/80">
        {visibles.map((serie, indice) => (
          <li key={serie.nombre}>
            {dosSeries ? `${serie.nombre} · ` : ""}
            {etiquetaPeriodo(periodos[0])}: <span className="text-2xl text-ink">{formatoNumero(valores[indice][0])}</span>
          </li>
        ))}
      </ul>
    );
  } else {
    const coordenadas = valores.map((lista) => coordenadasLinea(lista, 100, ALTO, 0, tope));
    const etiquetadosX = indicesEtiquetados(periodos.length);
    const ultimo = periodos.length - 1;
    const ancho = 100 / periodos.length;

    // Etiquetas directas del último valor; si se pisan, la de abajo baja un poco
    const yEtiquetas = coordenadas.map((lista) => lista[ultimo].y);
    if (yEtiquetas.length === 2 && Math.abs(yEtiquetas[0] - yEtiquetas[1]) < SEPARACION_ETIQUETAS) {
      const arriba = yEtiquetas[0] <= yEtiquetas[1] ? 0 : 1;
      const abajo = 1 - arriba;
      yEtiquetas[abajo] = yEtiquetas[arriba] + SEPARACION_ETIQUETAS;
      if (yEtiquetas[abajo] > ALTO) {
        yEtiquetas[abajo] = ALTO;
        yEtiquetas[arriba] = ALTO - SEPARACION_ETIQUETAS;
      }
    }

    const resumen = visibles
      .map((serie, indice) => `${serie.nombre}: ${formatoNumero(valores[indice][ultimo])} en ${etiquetaPeriodo(periodos[ultimo])}`)
      .join("; ");

    contenido = (
      <>
        {dosSeries ? (
          <ul className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-ink/80">
            {visibles.map((serie, indice) => (
              <li key={serie.nombre} className="flex items-center gap-2">
                <span aria-hidden="true" className={`h-0.5 w-5 rounded-full ${COLORES[indice]}`} />
                {serie.nombre}
              </li>
            ))}
          </ul>
        ) : null}

        <div
          role="img"
          aria-label={`${titulo}, de ${etiquetaPeriodo(periodos[0])} a ${etiquetaPeriodo(periodos[ultimo])}. ${resumen}.`}
          className="w-full pt-3 pr-14 pb-8 pl-10 sm:pr-36"
        >
          <div className="relative w-full" style={{ height: ALTO }}>
            {/* Grilla y eje Y: recesivos y sólidos */}
            {marcas.map((marca) => {
              const y = ALTO - (marca / tope) * ALTO;
              return (
                <div key={marca} className="absolute right-0 left-0" style={{ top: y }}>
                  <div className={`border-t ${marca === 0 ? "border-ink/15" : "border-ink/10"}`} />
                  <span className="absolute right-full mr-2 -translate-y-1/2 text-xs text-ink/60">
                    {formatoNumero(marca)}
                  </span>
                </div>
              );
            })}

            <svg
              aria-hidden="true"
              className="absolute inset-0 h-full w-full overflow-visible"
              viewBox={`0 0 100 ${ALTO}`}
              preserveAspectRatio="none"
            >
              {valores.map((lista, indice) => (
                <polyline
                  key={visibles[indice].nombre}
                  points={puntosLinea(lista, 100, ALTO, 0, tope)}
                  fill="none"
                  stroke={TRAZOS[indice]}
                  strokeWidth={2}
                  strokeLinejoin="round"
                  strokeLinecap="round"
                  vectorEffect="non-scaling-stroke"
                />
              ))}
            </svg>

            {/* Marcador del último punto y etiqueta directa (texto en ink, no en el color de la serie) */}
            {coordenadas.map((lista, indice) => (
              <div key={visibles[indice].nombre}>
                <span
                  aria-hidden="true"
                  className={`absolute h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full ${COLORES[indice]}`}
                  style={{ left: `${lista[ultimo].x}%`, top: lista[ultimo].y }}
                />
                <span
                  aria-hidden="true"
                  className="absolute left-full ml-3 -translate-y-1/2 text-xs whitespace-nowrap text-ink"
                  style={{ top: yEtiquetas[indice] }}
                >
                  <span className="hidden sm:inline">{visibles[indice].nombre}: </span>
                  {formatoNumero(valores[indice][ultimo])}
                </span>
              </div>
            ))}

            {/* Zonas de hover: una franja por período, más grande que el punto */}
            {periodos.map((periodo, indicePeriodo) => {
              const x = coordenadas[0][indicePeriodo].x;
              const alineacion =
                indicePeriodo === 0 ? "left-0" : indicePeriodo === ultimo ? "right-0" : "left-1/2 -translate-x-1/2";
              return (
                <div
                  key={periodo}
                  aria-hidden="true"
                  className="group absolute top-0 bottom-0"
                  style={{ left: `${x - ancho / 2}%`, width: `${ancho}%` }}
                >
                  <div className="absolute top-0 bottom-0 left-1/2 hidden w-px bg-ink/15 group-hover:block" />
                  {coordenadas.map((lista, indiceSerie) => (
                    <span
                      key={visibles[indiceSerie].nombre}
                      className={`absolute left-1/2 hidden h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-paper group-hover:block ${COLORES[indiceSerie]}`}
                      style={{ top: lista[indicePeriodo].y }}
                    />
                  ))}
                  <div
                    className={`pointer-events-none absolute -top-2 z-10 hidden -translate-y-full rounded-lg border-2 border-ink bg-paper px-2.5 py-1.5 text-xs whitespace-nowrap text-ink shadow-md group-hover:block ${alineacion}`}
                  >
                    <p className="font-medium">{etiquetaPeriodo(periodo)}</p>
                    {visibles.map((serie, indiceSerie) => (
                      <p key={serie.nombre}>
                        {dosSeries ? `${serie.nombre}: ` : ""}
                        {formatoNumero(valores[indiceSerie][indicePeriodo])}
                      </p>
                    ))}
                  </div>
                </div>
              );
            })}

            {/* Eje X */}
            {etiquetadosX.map((indice) => (
              <span
                key={periodos[indice]}
                className={`absolute top-full mt-2 text-xs whitespace-nowrap text-ink/60 ${
                  indice === 0 && periodos.length > 1 ? "" : indice === ultimo ? "-translate-x-full" : "-translate-x-1/2"
                }`}
                style={{ left: `${coordenadas[0][indice].x}%` }}
              >
                {etiquetaPeriodo(periodos[indice])}
              </span>
            ))}
          </div>
        </div>
      </>
    );
  }

  return (
    <figure className="grafico-analisis flex min-w-0 flex-col gap-3 rounded-3xl border-2 border-ink bg-paper p-5">
      <figcaption className="text-base font-medium text-ink">{titulo}</figcaption>
      {contenido}
      {nota ? <p className="text-xs text-ink/60">{nota}</p> : null}
      {hayDatos ? (
        <details className="text-sm text-ink">
          <summary className="cursor-pointer text-ink/70 hover:text-ink">Ver tabla</summary>
          <div className="mt-2 max-w-full overflow-x-auto">
            <table className="w-full text-left text-sm">
              <caption className="sr-only">{titulo}</caption>
              <thead>
                <tr className="border-b border-ink/15 text-ink/70">
                  <th scope="col" className="py-1 pr-3 font-normal">Período</th>
                  {visibles.map((serie) => (
                    <th key={serie.nombre} scope="col" className="py-1 pr-3 text-right font-normal">
                      {dosSeries ? serie.nombre : "Cantidad"}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {periodos.map((periodo, indicePeriodo) => (
                  <tr key={periodo} className="border-b border-ink/10">
                    <th scope="row" className="py-1 pr-3 font-normal">{etiquetaPeriodo(periodo)}</th>
                    {valores.map((lista, indiceSerie) => (
                      <td key={visibles[indiceSerie].nombre} className="py-1 pr-3 text-right tabular-nums">
                        {formatoNumero(lista[indicePeriodo])}
                      </td>
                    ))}
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
