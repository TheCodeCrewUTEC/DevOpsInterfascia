import Link from "next/link";
import { filtrosNoAplicados, hrefAnalisis, type AnalisisTendencias, type Agrupar, type Filtros } from "@/lib/analisis";
import GraficoLineas from "./GraficoLineas";
import NoDisponible from "./NoDisponible";

// Evolución en el tiempo (RF006-05): fondos por apertura y cierre, proyectos e incorporaciones

interface VistaTendenciasProps {
  datos: AnalisisTendencias;
  filtros: Filtros;
}

const AGRUPACIONES: { valor: Agrupar; label: string }[] = [
  { valor: "anio", label: "Por año" },
  { valor: "mes", label: "Por mes" },
];

type Entidad = "fondos" | "proyectos" | "investigadores";

// Aviso por gráfico de los filtros activos que no aplican a esa entidad.
// Si la API no manda filtros_aplicados (versión vieja) no se avisa nada.
function AvisoEntidad({ datos, filtros, entidad }: VistaTendenciasProps & { entidad: Entidad }) {
  const aplicados = datos.filtros_aplicados?.[entidad];
  if (!aplicados) return null;

  const etiquetas = filtrosNoAplicados(filtros, aplicados);
  if (etiquetas.length === 0) return null;

  const texto =
    etiquetas.length === 1
      ? `El filtro ${etiquetas[0]} no aplica a ${entidad}.`
      : `Los filtros ${etiquetas.slice(0, -1).join(", ")} y ${etiquetas[etiquetas.length - 1]} no aplican a ${entidad}.`;

  return (
    <p role="status" className="rounded-2xl border-2 border-gold bg-gold/15 px-4 py-2.5 text-sm text-ink">
      {texto}
    </p>
  );
}

export default function VistaTendencias({ datos, filtros }: VistaTendenciasProps) {
  return (
    <div className="flex flex-col gap-4">
      <nav className="flex flex-wrap gap-2" aria-label="Agrupar por">
        {AGRUPACIONES.map((opcion) => (
          <Link
            key={opcion.valor}
            href={hrefAnalisis(filtros, { agrupar: opcion.valor })}
            aria-current={opcion.valor === filtros.agrupar ? "true" : undefined}
            className={
              opcion.valor === filtros.agrupar
                ? "presionable inline-flex min-h-9 items-center rounded-full border-2 border-ink bg-ink px-4 text-sm text-paper pointer-coarse:min-h-11"
                : "presionable inline-flex min-h-9 items-center rounded-full border-2 border-ink bg-paper px-4 text-sm text-ink hover:bg-foam pointer-coarse:min-h-11"
            }
          >
            {opcion.label}
          </Link>
        ))}
      </nav>

      {datos.disponible.fondos ? (
        <div className="flex flex-col gap-2">
          <AvisoEntidad datos={datos} filtros={filtros} entidad="fondos" />
          <GraficoLineas
            titulo="Fondos por fecha de apertura y de cierre"
            series={[
              { nombre: "Por apertura", puntos: datos.fondos_por_apertura },
              { nombre: "Por cierre", puntos: datos.fondos_por_cierre },
            ]}
          />
        </div>
      ) : (
        <NoDisponible titulo="Fondos" motivo="No hay datos de fondos cargados en la plataforma." />
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {datos.disponible.proyectos ? (
          <div className="flex min-w-0 flex-col gap-2">
            <AvisoEntidad datos={datos} filtros={filtros} entidad="proyectos" />
            <GraficoLineas
              titulo="Proyectos por año"
              series={[{ nombre: "Proyectos", puntos: datos.proyectos_por_anio }]}
            />
          </div>
        ) : (
          <NoDisponible titulo="Proyectos" motivo="No hay datos de proyectos cargados en la plataforma." />
        )}

        {datos.disponible.investigadores ? (
          <div className="flex min-w-0 flex-col gap-2">
            <AvisoEntidad datos={datos} filtros={filtros} entidad="investigadores" />
            <GraficoLineas
              titulo="Investigadores incorporados a Interfascia (fecha de carga)"
              series={[{ nombre: "Investigadores", puntos: datos.investigadores_incorporados }]}
              nota="Cuenta cuándo se cargó cada perfil en la plataforma, no su trayectoria."
            />
          </div>
        ) : (
          <NoDisponible titulo="Investigadores" motivo="No hay datos de investigadores cargados en la plataforma." />
        )}
      </div>
    </div>
  );
}
