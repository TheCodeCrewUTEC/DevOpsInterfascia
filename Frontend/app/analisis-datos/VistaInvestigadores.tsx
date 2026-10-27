import { FORMACIONES, formatoNumero, type AnalisisInvestigadores, type Filtros } from "@/lib/analisis";
import AvisoFiltros, { NOTA_TEMATICA } from "./AvisoFiltros";
import GraficoBarras from "./GraficoBarras";
import GraficoTorta from "./GraficoTorta";
import Indicador from "./Indicador";
import NoDisponible from "./NoDisponible";

// Distribución de investigadores (RF006-03): institución, SNI, formación y área temática

interface VistaInvestigadoresProps {
  datos: AnalisisInvestigadores;
  filtros: Filtros;
}

export default function VistaInvestigadores({ datos, filtros }: VistaInvestigadoresProps) {
  if (!datos.disponible) {
    return <NoDisponible motivo="No hay datos de investigadores cargados en la plataforma." />;
  }

  const lineas = datos.lineas_investigacion;

  return (
    <div className="flex flex-col gap-4">
      <AvisoFiltros filtros={filtros} aplicados={datos.filtros_aplicados} />

      {datos.total === 0 ? (
        <p className="rounded-3xl border-2 border-ink bg-paper p-5 text-sm text-ink/70">No hay datos para estos filtros.</p>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Indicador etiqueta="Investigadores" valor={datos.total} />
            <Indicador
              etiqueta="Líneas de investigación"
              valor={lineas.total}
              nota={`${formatoNumero(lineas.promedio_por_investigador, 1)} por investigador en promedio`}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <GraficoBarras titulo="Investigadores por institución" serie={datos.por_institucion} total={datos.total} />
            <GraficoBarras titulo="Investigadores por área temática" serie={datos.por_area_tematica} nota={NOTA_TEMATICA} />
            <GraficoTorta titulo="Investigadores por nivel SNI" serie={datos.por_nivel_sni} />
            <GraficoTorta titulo="Investigadores por categoría SNI" serie={datos.por_categoria_sni} />
            <GraficoTorta titulo="Investigadores por formación" serie={datos.por_formacion} conocidas={FORMACIONES} />
          </div>
        </>
      )}
    </div>
  );
}
