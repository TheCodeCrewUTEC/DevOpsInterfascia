import { formatoNumero, porcentaje, type AnalisisFondos, type Filtros } from "@/lib/analisis";
import AvisoFiltros, { NOTA_TEMATICA } from "./AvisoFiltros";
import GraficoBarras from "./GraficoBarras";
import Indicador from "./Indicador";
import NoDisponible from "./NoDisponible";

// Distribución de fondos (RF006-02): organismo, temática, estado y año de apertura

interface VistaFondosProps {
  datos: AnalisisFondos;
  filtros: Filtros;
}

export default function VistaFondos({ datos, filtros }: VistaFondosProps) {
  if (!datos.disponible) {
    return <NoDisponible motivo="No hay datos de fondos cargados en la plataforma." />;
  }

  const { informado, sin_informar } = datos.financiamiento;

  return (
    <div className="flex flex-col gap-4">
      <AvisoFiltros filtros={filtros} aplicados={datos.filtros_aplicados} />

      {datos.total === 0 ? (
        <p className="rounded-3xl border-2 border-ink bg-paper p-5 text-sm text-ink/70">No hay datos para estos filtros.</p>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Indicador etiqueta="Fondos" valor={datos.total} />
            <Indicador
              etiqueta="Con financiamiento informado"
              valor={informado}
              nota={`${porcentaje(informado, informado + sin_informar)} del total · ${formatoNumero(sin_informar)} sin informar`}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <GraficoBarras titulo="Fondos por organismo" serie={datos.por_organismo} total={datos.total} />
            <GraficoBarras
              titulo="Fondos por área temática"
              serie={datos.por_tematica}
              nota={datos.tematica_multiple ? NOTA_TEMATICA : undefined}
            />
            <GraficoBarras titulo="Fondos por estado de convocatoria" serie={datos.por_estado} total={datos.total} />
            <GraficoBarras titulo="Fondos por año de apertura" serie={datos.por_anio_apertura} total={datos.total} />
          </div>
        </>
      )}

      <NoDisponible titulo="Fondos por sector económico" motivo={datos.por_sector_economico.motivo} />
    </div>
  );
}
