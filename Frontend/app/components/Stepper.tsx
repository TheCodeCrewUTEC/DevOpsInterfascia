// Indicador de pasos para formularios largos. Los pasos ya hechos se pueden
// volver a abrir con un click; los siguientes se habilitan al avanzar.

interface StepperProps {
  pasos: string[];
  actual: number;
  onIrA?: (indice: number) => void;
}

export default function Stepper({ pasos, actual, onIrA }: StepperProps) {
  return (
    <nav aria-label="Pasos del formulario">
      <ol className="flex flex-wrap items-center gap-x-2 gap-y-3">
        {pasos.map((paso, indice) => {
          const hecho = indice < actual;
          const activo = indice === actual;
          const clickeable = hecho && onIrA;

          const circulo = (
            <span
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-sm font-medium transition ${
                activo
                  ? "border-ink bg-pine text-ink"
                  : hecho
                    ? "border-pine bg-pine/20 text-ink"
                    : "border-ink/30 bg-paper text-ink/60"
              }`}
            >
              {hecho ? "✓" : indice + 1}
            </span>
          );

          const texto = (
            <span className={`text-sm ${activo ? "font-medium text-ink" : "text-ink/70"}`}>{paso}</span>
          );

          return (
            <li key={paso} className="flex items-center gap-2" aria-current={activo ? "step" : undefined}>
              {clickeable ? (
                <button type="button" onClick={() => onIrA(indice)} className="flex items-center gap-2 rounded-full pr-2 transition hover:bg-foam">
                  {circulo}
                  {texto}
                </button>
              ) : (
                <span className="flex items-center gap-2">
                  {circulo}
                  {texto}
                </span>
              )}
              {indice < pasos.length - 1 ? (
                <span aria-hidden="true" className={`mx-1 h-0.5 w-8 rounded-full sm:w-14 ${hecho ? "bg-pine" : "bg-ink/20"}`} />
              ) : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
