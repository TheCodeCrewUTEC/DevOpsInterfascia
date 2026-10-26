import type { AnalisisProyectos, Filtros } from "@/lib/analisis";
import AvisoFiltros, { NOTA_TEMATICA } from "./AvisoFiltros";
import GraficoBarras from "./GraficoBarras";
import Indicador from "./Indicador";
import NoDisponible from "./NoDisponible";

// Distribución de proyectos (RF006-04): estado, año y área temática

interface VistaProyectosProps {
  datos: AnalisisProyectos;
  filtros: Filtros;
}

export default function VistaProyectos({ datos, filtros }: VistaProyectosProps) {
  if (!datos.disponible) {
    return <NoDisponible motivo="No hay datos de proyectos cargados en la plataforma." />;
  }

  return (
    <div className="flex flex-col gap-4">
      <AvisoFiltros filtros={filtros} aplicados={datos.filtros_aplicados} />

      {datos.total === 0 ? (
        <p className="rounded-3xl border-2 border-ink bg-paper p-5 text-sm text-ink/70">No hay datos para estos filtros.</p>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Indicador etiqueta="Proyectos" valor={datos.total} />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <GraficoBarras titulo="Proyectos por estado" serie={datos.por_estado} total={datos.total} />
            <GraficoBarras titulo="Proyectos por año" serie={datos.por_anio} total={datos.total} />
            <GraficoBarras titulo="Proyectos por área temática" serie={datos.por_tematica} nota={NOTA_TEMATICA} />
          </div>
        </>
      )}

      <NoDisponible titulo="Proyectos por organismo" motivo={datos.por_organismo.motivo} />
    </div>
  );
}
