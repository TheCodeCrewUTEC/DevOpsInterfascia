// Tipos y utilidades de las alertas (RF005). Sin dependencias de servidor:
// lo usan tanto las páginas como los componentes de cliente y los tests.

export type TipoAlerta = "apertura" | "cierre" | "actualizacion";

export type Notificacion = {
  id: number;
  tipo: string;
  convocatoria_id: number | null;
  titulo: string;
  mensaje: string;
  // 'actualizacion': [{campo, antes, despues}]; 'cierre': {dias_restantes, fecha_cierre}
  detalle: unknown;
  leida: boolean;
  creado: string;
  email_enviado_en: string | null;
};

export type PaginaNotificaciones = {
  items: Notificacion[];
  page: number;
  limit: number;
  total: number;
  total_pages: number;
  no_leidas: number;
};

export type Preferencias = {
  alerta_apertura: boolean;
  alerta_cierre: boolean;
  alerta_actualizacion: boolean;
  dias_anticipacion_cierre: number;
  email_habilitado: boolean;
  email: string | null;
};

export type Opciones = {
  tipos_alerta: string[];
  tematicas: string[];
  instituciones: string[];
};

export type Suscripcion = {
  id: number;
  tipo: "convocatoria" | "institucion" | "tematica";
  convocatoria_id: number | null;
  valor: string | null;
  titulo_convocatoria: string | null;
  creado: string;
};

export type FilaCambio = { campo: string; antes: string; despues: string };

export const DIAS_MINIMO = 1;
export const DIAS_MAXIMO = 60;
export const LIMITE_NOTIFICACIONES = 20;

const ETIQUETAS_TIPO: Record<string, string> = {
  apertura: "Apertura",
  cierre: "Próximo cierre",
  actualizacion: "Actualización",
};

export function etiquetaTipo(tipo: string) {
  return ETIQUETAS_TIPO[tipo] ?? tipo;
}

const NOMBRES_CAMPO: Record<string, string> = {
  titulo: "Título",
  institucion: "Institución",
  estado: "Estado",
  fecha_apertura: "Fecha de apertura",
  fecha_cierre: "Fecha de cierre",
  descripcion: "Descripción",
  beneficiarios: "Beneficiarios",
  requisitos: "Requisitos",
  financiamiento: "Financiamiento",
};

export const LARGO_MAXIMO_VALOR = 200;

const FECHA_ISO = /^(\d{4})-(\d{2})-(\d{2})$/;

// Fechas ISO (YYYY-MM-DD) como dd/mm/aaaa y textos largos recortados con "…"
export function valorLegible(valor: unknown) {
  if (valor === null || valor === undefined || valor === "") return "—";
  if (typeof valor === "number" || typeof valor === "boolean") return String(valor);

  const texto = typeof valor === "string" ? valor : JSON.stringify(valor);
  const fecha = FECHA_ISO.exec(texto);
  if (fecha) return `${fecha[3]}/${fecha[2]}/${fecha[1]}`;
  if (texto.length <= LARGO_MAXIMO_VALOR) return texto;
  return `${texto.slice(0, LARGO_MAXIMO_VALOR - 1).trimEnd()}…`;
}

// Filas Campo/Antes/Después de una notificación de actualización.
// Tolera detalle null o con otra forma: lo que no se entiende se descarta.
export function filasCambios(detalle: unknown): FilaCambio[] {
  if (!Array.isArray(detalle)) return [];

  return detalle.flatMap((cambio) => {
    if (!cambio || typeof cambio !== "object") return [];
    const { campo, antes, despues } = cambio as Record<string, unknown>;
    if (typeof campo !== "string" || !campo) return [];
    return [
      {
        campo: NOMBRES_CAMPO[campo] ?? campo,
        antes: valorLegible(antes),
        despues: valorLegible(despues),
      },
    ];
  });
}

// Días restantes de una notificación de cierre, o null si el detalle no los trae
export function diasRestantes(detalle: unknown): number | null {
  if (!detalle || typeof detalle !== "object" || Array.isArray(detalle)) return null;
  const dias = (detalle as Record<string, unknown>).dias_restantes;
  return typeof dias === "number" && Number.isFinite(dias) ? dias : null;
}

export function agruparSuscripciones(lista: Suscripcion[]) {
  return {
    fondos: lista.filter((suscripcion) => suscripcion.tipo === "convocatoria"),
    instituciones: lista.filter((suscripcion) => suscripcion.tipo === "institucion"),
    tematicas: lista.filter((suscripcion) => suscripcion.tipo === "tematica"),
  };
}

// Mismo rango que valida la API (1..60); devuelve el mensaje de error o null
export function validarDias(dias: number): string | null {
  if (!Number.isInteger(dias) || dias < DIAS_MINIMO || dias > DIAS_MAXIMO) {
    return `Indicá un número entero de días entre ${DIAS_MINIMO} y ${DIAS_MAXIMO}.`;
  }
  return null;
}

export function fechaLegible(iso: string) {
  const fecha = new Date(iso);
  if (Number.isNaN(fecha.getTime())) return iso;
  return fecha.toLocaleString("es-UY", { dateStyle: "medium", timeStyle: "short" });
}

// Mensaje de error de la API ({"detail": "..."}) para mostrar al usuario
export async function detalleRespuesta(response: Response) {
  try {
    const datos = (await response.json()) as { detail?: unknown };
    return typeof datos.detail === "string" ? datos.detail : `Error ${response.status}`;
  } catch {
    return `Error ${response.status}`;
  }
}

// Nombre legible de una suscripción para los avisos ("Dejaste de seguir …")
export function nombreSuscripcion(suscripcion: Suscripcion) {
  if (suscripcion.tipo === "convocatoria") {
    return suscripcion.titulo_convocatoria?.trim() || `la convocatoria #${suscripcion.convocatoria_id ?? suscripcion.id}`;
  }
  return suscripcion.valor?.trim() || `la suscripción #${suscripcion.id}`;
}

// Cuerpo del POST que vuelve a crear una suscripción borrada (para "Deshacer").
// null si le falta el dato que la identifica: en ese caso no se ofrece deshacer.
export function cuerpoSuscripcion(suscripcion: Suscripcion) {
  if (suscripcion.tipo === "convocatoria") {
    return suscripcion.convocatoria_id !== null
      ? { tipo: suscripcion.tipo, convocatoria_id: suscripcion.convocatoria_id }
      : null;
  }
  return suscripcion.valor?.trim() ? { tipo: suscripcion.tipo, valor: suscripcion.valor } : null;
}
