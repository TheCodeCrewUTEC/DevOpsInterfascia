// Suscripciones a alertas de fondos (convocatorias) y helpers compartidos del repositorio.

export type TipoSuscripcion = "convocatoria" | "institucion" | "tematica";

export type Suscripcion = {
  id: number;
  tipo: TipoSuscripcion;
  convocatoria_id: number | null;
  valor: string | null;
  titulo_convocatoria: string | null;
  creado: string | null;
};

function normalizar(valor: string | null | undefined) {
  return valor?.trim().toLowerCase() ?? "";
}

// Busca la suscripción de un tipo: por id de convocatoria o por valor (sin distinguir mayúsculas)
export function buscarSuscripcion(
  lista: Suscripcion[],
  tipo: TipoSuscripcion,
  { convocatoriaId, valor }: { convocatoriaId?: number; valor?: string | null },
): Suscripcion | null {
  const buscado = normalizar(valor);
  return (
    lista.find((item) => {
      if (item.tipo !== tipo) return false;
      if (convocatoriaId !== undefined) return item.convocatoria_id === convocatoriaId;
      return Boolean(buscado) && normalizar(item.valor) === buscado;
    }) ?? null
  );
}

// "2026-03-15" o "2026-03-15T10:00:00" → "15/03/2026"
export function formatFecha(valor: string | null | undefined) {
  if (!valor) return "Sin fecha";
  const [anio, mes, dia] = valor.slice(0, 10).split("-");
  if (!anio || !mes || !dia) return valor;
  return `${dia}/${mes}/${anio}`;
}
