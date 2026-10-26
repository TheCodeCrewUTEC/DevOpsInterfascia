import { avisoNoAplicados, filtrosNoAplicados, type Filtros } from "@/lib/analisis";

// Avisa qué filtros activos no se pueden aplicar a una sección (p. ej. "Estado" en investigadores)

export const NOTA_TEMATICA =
  "El área temática se deriva por coincidencia de texto; un registro puede contar en varias áreas.";

interface AvisoFiltrosProps {
  filtros: Filtros;
  aplicados: readonly string[];
}

export default function AvisoFiltros({ filtros, aplicados }: AvisoFiltrosProps) {
  const texto = avisoNoAplicados(filtrosNoAplicados(filtros, aplicados));
  if (!texto) return null;

  return (
    <p role="status" className="rounded-2xl border-2 border-gold bg-gold/15 px-4 py-2.5 text-sm text-ink">
      {texto}
    </p>
  );
}
