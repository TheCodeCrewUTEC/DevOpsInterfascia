import type { ReactNode } from "react";
import { porcentaje, type Filtros, type ResumenAnalisis } from "@/lib/analisis";
import AvisoFiltros from "./AvisoFiltros";
import Indicador from "./Indicador";
import NoDisponible from "./NoDisponible";

// Indicadores generales (RF006-01): un grupo de tarjetas por entidad

interface VistaResumenProps {
  datos: ResumenAnalisis;
  filtros: Filtros;
}

function Grupo({
  titulo,
  entidad,
  disponible,
  total,
  aplicados,
  filtros,
  children,
}: {
  titulo: string;
  entidad: string;
  disponible: boolean;
  total: number;
  aplicados: readonly string[];
  filtros: Filtros;
  children: ReactNode;
}) {
  return (
    <section className="flex flex-col gap-3" aria-labelledby={`grupo-${entidad}`}>
      <h2 id={`grupo-${entidad}`} className="font-display text-2xl text-ink">
        {titulo}
      </h2>
      {!disponible ? (
        <NoDisponible motivo={`No hay datos de ${entidad} cargados en la plataforma.`} />
      ) : (
        <>
          <AvisoFiltros filtros={filtros} aplicados={aplicados} />
          {total === 0 ? (
            <p className="rounded-3xl border-2 border-ink bg-paper p-5 text-sm text-ink/70">
              No hay datos para estos filtros.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{children}</div>
          )}
        </>
      )}
    </section>
  );
}

export default function VistaResumen({ datos, filtros }: VistaResumenProps) {
  const { fondos, investigadores, proyectos } = datos;
  const generado = new Date(datos.generado);

  return (
    <div className="flex flex-col gap-8">
      <Grupo
        titulo="Fondos"
        entidad="fondos"
        disponible={fondos.disponible}
        total={fondos.total}
        aplicados={fondos.filtros_aplicados}
        filtros={filtros}
      >
        <Indicador etiqueta="Fondos" valor={fondos.total} />
        <Indicador etiqueta="Abiertos" valor={fondos.abiertos} nota={`${porcentaje(fondos.abiertos, fondos.total)} del total`} />
        <Indicador etiqueta="Próximos a abrir" valor={fondos.proximos} />
        <Indicador etiqueta="Cerrados" valor={fondos.cerrados} />
        <Indicador etiqueta="Cierran en los próximos 30 días" valor={fondos.cierran_30_dias} />
        <Indicador etiqueta="Organismos financiadores" valor={fondos.organismos} />
        <Indicador
          etiqueta="Con financiamiento informado"
          valor={fondos.con_financiamiento}
          nota={`${porcentaje(fondos.con_financiamiento, fondos.total)} del total`}
        />
      </Grupo>

      <Grupo
        titulo="Investigadores"
        entidad="investigadores"
        disponible={investigadores.disponible}
        total={investigadores.total}
        aplicados={investigadores.filtros_aplicados}
        filtros={filtros}
      >
        <Indicador etiqueta="Investigadores" valor={investigadores.total} />
        <Indicador etiqueta="Instituciones" valor={investigadores.instituciones} />
        <Indicador
          etiqueta="Con nivel SNI"
          valor={investigadores.con_nivel_sni}
          nota={`${porcentaje(investigadores.con_nivel_sni, investigadores.total)} del total`}
        />
      </Grupo>

      <Grupo
        titulo="Proyectos"
        entidad="proyectos"
        disponible={proyectos.disponible}
        total={proyectos.total}
        aplicados={proyectos.filtros_aplicados}
        filtros={filtros}
      >
        <Indicador etiqueta="Proyectos" valor={proyectos.total} />
        <Indicador etiqueta="En curso" valor={proyectos.en_curso} />
        <Indicador etiqueta="Finalizados" valor={proyectos.finalizados} />
      </Grupo>

      {Number.isNaN(generado.getTime()) ? null : (
        <p className="text-xs text-ink/60">
          Datos calculados el{" "}
          {generado.toLocaleString("es-UY", {
            dateStyle: "medium",
            timeStyle: "short",
            timeZone: "America/Montevideo",
          })}
          .
        </p>
      )}
    </div>
  );
}
