// Tarjeta con un solo número (KPI): un valor suelto no se grafica.

interface IndicadorProps {
  etiqueta: string;
  valor: string | number;
  nota?: string;
}

export default function Indicador({ etiqueta, valor, nota }: IndicadorProps) {
  return (
    <div className="flex min-w-0 flex-col rounded-3xl border-2 border-ink bg-paper p-5">
      <p className="text-sm text-ink/70">{etiqueta}</p>
      <p className="mt-2 font-sans text-4xl font-medium text-ink">
        {typeof valor === "number" ? valor.toLocaleString("es-UY") : valor}
      </p>
      {nota ? <p className="mt-1 text-xs text-ink/70">{nota}</p> : null}
    </div>
  );
}
