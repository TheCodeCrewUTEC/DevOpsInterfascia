import type { Metadata } from "next";
import { auth } from "@/auth";
import { apiFetch } from "@/lib/api";
import { ESTADOS_USUARIO, esFechaValida, queryDeFiltros } from "@/lib/analisis";
import { fechaCorta, type MetricasUso } from "@/lib/reportes";
import { esAdmin } from "@/lib/roles";
import BotonesExportar from "@/app/analisis-datos/BotonesExportar";
import GraficoBarras from "@/app/analisis-datos/GraficoBarras";
import GraficoLineas from "@/app/analisis-datos/GraficoLineas";
import GraficoTorta from "@/app/analisis-datos/GraficoTorta";
import Indicador from "@/app/analisis-datos/Indicador";
import FiltroPeriodo from "./FiltroPeriodo";
import "@/app/analisis-datos/graficos.css";

export const metadata: Metadata = {
  title: "Métricas de uso | Interfascia",
};

export const dynamic = "force-dynamic";

// Si el parámetro vino repetido se queda con el primero
function primero(valor: string | string[] | undefined) {
  return ((Array.isArray(valor) ? valor[0] : valor) ?? "").trim();
}

// Métricas de uso de la plataforma (RF006-08), solo para administradores
export default async function MetricasUsoPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const session = await auth();

  if (!esAdmin(session)) {
    return (
      <Encabezado>
        <Aviso texto="Esta página es solo para administradores." />
      </Encabezado>
    );
  }

  let desde = primero(params.desde);
  let hasta = primero(params.hasta);
  const fechasInvalidas = (desde !== "" && !esFechaValida(desde)) || (hasta !== "" && !esFechaValida(hasta));
  if (!esFechaValida(desde)) desde = "";
  if (!esFechaValida(hasta)) hasta = "";
  if (desde && hasta && desde > hasta) [desde, hasta] = [hasta, desde];

  const query = queryDeFiltros({}, { desde, hasta });
  let datos: MetricasUso | null = null;
  let error: string | null = null;

  try {
    const response = await apiFetch(`/api/admin/analisis/uso${query ? `?${query}` : ""}`, { cache: "no-store" });
    if (response.ok) {
      datos = (await response.json()) as MetricasUso;
    } else {
      const cuerpo = await response.json().catch(() => null);
      error =
        typeof cuerpo?.detail === "string"
          ? cuerpo.detail
          : `No se pudieron cargar las métricas (${response.status}).`;
    }
  } catch {
    error = "No se pudo conectar con la API.";
  }

  // Se exporta el rango que efectivamente devolvió la API
  const rango = { desde: datos?.desde ?? desde, hasta: datos?.hasta ?? hasta };

  return (
    <Encabezado
      acciones={
        <BotonesExportar
          hrefs={{
            csv: `/analisis-datos/exportar?${queryDeFiltros(rango, { formato: "csv", vista: "uso" })}`,
            pdf: `/analisis-datos/exportar?${queryDeFiltros(rango, { formato: "pdf", vista: "uso" })}`,
          }}
        />
      }
    >
      <FiltroPeriodo key={`${desde}|${hasta}`} desde={desde} hasta={hasta} />

      {fechasInvalidas ? (
        <Aviso texto="Alguna de las fechas no es válida (formato AAAA-MM-DD); se ignoró." />
      ) : null}
      {error ? <Aviso texto={error} /> : null}

      {datos ? (
        <>
          <p className="text-sm text-ink/70">
            Del {fechaCorta(datos.desde)} al {fechaCorta(datos.hasta)}.
          </p>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Indicador etiqueta="Total de eventos" valor={datos.total_eventos} />
            <Indicador etiqueta="Usuarios distintos" valor={datos.usuarios_distintos} />
            <Indicador etiqueta="Búsquedas" valor={datos.busquedas} />
            <Indicador
              etiqueta="Usuarios registrados"
              valor={datos.usuarios_registrados.total}
              nota="En total, no solo en este período"
            />
          </div>

          {datos.total_eventos === 0 ? (
            <p className="rounded-3xl border-2 border-ink bg-paper p-5 text-sm text-ink/70">
              Todavía no hay actividad registrada en este período.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <GraficoBarras
                titulo="Uso por funcionalidad"
                serie={datos.por_funcionalidad.map(({ etiqueta, cantidad }) => ({ etiqueta, cantidad }))}
                total={datos.total_eventos}
              />
              <GraficoLineas
                titulo="Actividad por día"
                series={[{ nombre: "Eventos", puntos: datos.por_dia }]}
              />
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <GraficoTorta
              titulo="Usuarios registrados por estado"
              serie={datos.usuarios_registrados.por_estado}
              conocidas={ESTADOS_USUARIO}
            />
            {/* Torta solo con 3 a 6 perfiles; con más (o menos) queda en barras */}
            <GraficoTorta
              titulo="Usuarios registrados por perfil"
              serie={datos.usuarios_registrados.por_perfil}
              agrupar={false}
            />
          </div>
        </>
      ) : null}
    </Encabezado>
  );
}

function Encabezado({ acciones, children }: { acciones?: React.ReactNode; children: React.ReactNode }) {
  return (
    <main className="mx-auto flex w-full max-w-[100rem] flex-1 flex-col gap-6 px-6 py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium tracking-[0.18em] text-clay uppercase">Administración</p>
          <h1 className="font-display mt-2 text-4xl text-balance text-ink">Métricas de uso</h1>
          <p className="mt-2 text-sm text-ink/70">
            Qué funcionalidades se usan, cuánto y por cuántos usuarios. Por defecto, los últimos 30 días.
          </p>
        </div>
        {acciones ? <div className="flex flex-wrap gap-2">{acciones}</div> : null}
      </div>
      {children}
    </main>
  );
}

function Aviso({ texto }: { texto: string }) {
  return (
    <p role="alert" className="rounded-2xl border border-clay/30 bg-clay/10 px-4 py-3 text-sm text-ink">
      {texto}
    </p>
  );
}
