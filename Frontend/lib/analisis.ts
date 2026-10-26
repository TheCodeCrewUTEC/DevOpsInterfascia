// Tipos y utilidades del análisis de datos (RF006). Sin dependencias de servidor:
// lo usan la página, los componentes de cliente y los tests.

// ============================================================
// CONTRATO DE LA API (/api/analisis/*)
// ============================================================

export type Serie = { etiqueta: string; cantidad: number }[];

export type PuntoTiempo = { periodo: string; cantidad: number };

export type NoDisponibleApi = { disponible: false; motivo: string };

export type ClaveFiltro = "organismo" | "tematica" | "estado" | "periodo";

export type OpcionesAnalisis = {
  organismos: string[];
  tematicas: string[];
  estados: string[];
  sector_economico: NoDisponibleApi;
};

type Seccion = {
  disponible: boolean;
  filtros_aplicados: ClaveFiltro[];
  total: number;
};

export type ResumenAnalisis = {
  filtros: Record<string, string | null>;
  fondos: Seccion & {
    abiertos: number;
    proximos: number;
    cerrados: number;
    cierran_30_dias: number;
    organismos: number;
    con_financiamiento: number;
  };
  investigadores: Seccion & {
    instituciones: number;
    con_nivel_sni: number;
  };
  proyectos: Seccion & {
    en_curso: number;
    finalizados: number;
  };
  generado: string;
};

export type AnalisisFondos = Seccion & {
  por_organismo: Serie;
  por_tematica: Serie;
  por_estado: Serie;
  por_anio_apertura: Serie;
  por_sector_economico: NoDisponibleApi;
  financiamiento: { informado: number; sin_informar: number };
  tematica_multiple: boolean;
};

export type AnalisisInvestigadores = Seccion & {
  por_institucion: Serie;
  por_nivel_sni: Serie;
  por_categoria_sni: Serie;
  por_formacion: Serie;
  por_area_tematica: Serie;
  lineas_investigacion: { total: number; promedio_por_investigador: number };
};

export type AnalisisProyectos = Seccion & {
  por_estado: Serie;
  por_anio: Serie;
  por_tematica: Serie;
  por_organismo: NoDisponibleApi;
};

export type AnalisisTendencias = {
  agrupar: Agrupar;
  fondos_por_apertura: PuntoTiempo[];
  fondos_por_cierre: PuntoTiempo[];
  proyectos_por_anio: PuntoTiempo[];
  investigadores_incorporados: PuntoTiempo[];
  disponible: { fondos: boolean; proyectos: boolean; investigadores: boolean };
  // Opcional: las respuestas viejas no lo traen y entonces no se avisa nada
  filtros_aplicados?: { fondos: ClaveFiltro[]; proyectos: ClaveFiltro[]; investigadores: ClaveFiltro[] };
};

// ============================================================
// FILTROS Y VISTAS
// ============================================================

export const VISTAS = ["resumen", "fondos", "investigadores", "proyectos", "tendencias"] as const;
export type Vista = (typeof VISTAS)[number];

export const ETIQUETAS_VISTA: Record<Vista, string> = {
  resumen: "Indicadores",
  fondos: "Fondos",
  investigadores: "Investigadores",
  proyectos: "Proyectos",
  tendencias: "Tendencias",
};

export type Agrupar = "anio" | "mes";

export const ESTADOS = ["Abierta", "Próxima", "Cerrada", "Otro", "Sin estado"];

export type Filtros = {
  vista: Vista;
  organismo: string;
  tematica: string;
  estado: string;
  desde: string;
  hasta: string;
  agrupar: Agrupar;
};

export const FILTROS_VACIOS: Filtros = {
  vista: "resumen",
  organismo: "",
  tematica: "",
  estado: "",
  desde: "",
  hasta: "",
  agrupar: "anio",
};

type Params = Record<string, string | string[] | undefined>;

// Si el parámetro vino repetido (?a=1&a=2) se queda con el primero
function primero(valor: string | string[] | undefined) {
  const texto = Array.isArray(valor) ? valor[0] : valor;
  return (texto ?? "").trim();
}

// AAAA-MM-DD y además una fecha que existe (descarta 2025-02-30)
export function esFechaValida(texto: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(texto)) return false;
  const [anio, mes, dia] = texto.split("-").map(Number);
  const fecha = new Date(Date.UTC(anio, mes - 1, dia));
  return fecha.getUTCFullYear() === anio && fecha.getUTCMonth() === mes - 1 && fecha.getUTCDate() === dia;
}

// Lee los filtros de la URL; lo inválido o desconocido se descarta en silencio
export function leerFiltros(params: Params): Filtros {
  const vista = primero(params.vista);
  const agrupar = primero(params.agrupar);
  const estado = primero(params.estado);
  let desde = primero(params.desde);
  let hasta = primero(params.hasta);

  if (!esFechaValida(desde)) desde = "";
  if (!esFechaValida(hasta)) hasta = "";
  // Rango dado vuelta: se corrige en lugar de devolver vacío
  if (desde && hasta && desde > hasta) [desde, hasta] = [hasta, desde];

  return {
    vista: (VISTAS as readonly string[]).includes(vista) ? (vista as Vista) : "resumen",
    organismo: primero(params.organismo),
    tematica: primero(params.tematica),
    estado: ESTADOS.includes(estado) ? estado : "",
    desde,
    hasta,
    agrupar: agrupar === "mes" ? "mes" : "anio",
  };
}

// Query string (sin "?") con los filtros de datos; omite los vacíos
export function queryDeFiltros(
  filtros: Partial<Filtros>,
  extra: Record<string, string | undefined> = {},
) {
  const query = new URLSearchParams();
  const valores: Record<string, string | undefined> = {
    organismo: filtros.organismo,
    tematica: filtros.tematica,
    estado: filtros.estado,
    desde: filtros.desde,
    hasta: filtros.hasta,
    ...extra,
  };

  for (const [clave, valor] of Object.entries(valores)) {
    if (valor && valor.trim()) query.set(clave, valor.trim());
  }
  return query.toString();
}

// URL de la página con los filtros; vista y agrupación por defecto no se escriben
export function hrefAnalisis(filtros: Filtros, cambios: Partial<Filtros> = {}) {
  const final = { ...filtros, ...cambios };
  const query = queryDeFiltros(final, {
    vista: final.vista === "resumen" ? undefined : final.vista,
    agrupar: final.vista === "tendencias" && final.agrupar === "mes" ? "mes" : undefined,
  });
  return query ? `/analisis-datos?${query}` : "/analisis-datos";
}

export function etiquetaFiltro(clave: string) {
  const etiquetas: Record<string, string> = {
    organismo: "Organismo",
    tematica: "Área temática",
    estado: "Estado",
    periodo: "Período",
  };
  return etiquetas[clave] ?? clave;
}

// Claves de los filtros que el usuario tiene activos
export function filtrosActivos(filtros: Partial<Filtros>): ClaveFiltro[] {
  const activos: ClaveFiltro[] = [];
  if (filtros.organismo) activos.push("organismo");
  if (filtros.tematica) activos.push("tematica");
  if (filtros.estado) activos.push("estado");
  if (filtros.desde || filtros.hasta) activos.push("periodo");
  return activos;
}

// Etiquetas de los filtros activos que la sección no usa (para avisarlo)
export function filtrosNoAplicados(filtros: Partial<Filtros>, aplicados: readonly string[]) {
  return filtrosActivos(filtros)
    .filter((clave) => !aplicados.includes(clave))
    .map(etiquetaFiltro);
}

export function avisoNoAplicados(etiquetas: string[]) {
  if (etiquetas.length === 0) return null;
  if (etiquetas.length === 1) return `El filtro ${etiquetas[0]} no aplica a esta sección.`;
  const lista = `${etiquetas.slice(0, -1).join(", ")} y ${etiquetas[etiquetas.length - 1]}`;
  return `Los filtros ${lista} no aplican a esta sección.`;
}

// ============================================================
// GRÁFICOS
// ============================================================

// Largo de una barra en % del máximo de la serie (0..100)
export function anchoBarra(cantidad: number, maximo: number) {
  if (!(maximo > 0) || !(cantidad > 0)) return 0;
  return Math.min(100, (cantidad / maximo) * 100);
}

function redondear(valor: number) {
  return Math.round(valor * 100) / 100;
}

// Coordenadas de una línea dentro de ancho × alto (y crece hacia abajo).
// maximo permite compartir la escala entre varias series (mismo eje Y).
export function coordenadasLinea(
  valores: number[],
  ancho: number,
  alto: number,
  margen = 0,
  maximo?: number,
) {
  const tope = maximo ?? Math.max(0, ...valores);
  const base = alto - margen;
  const util = alto - margen * 2;

  return valores.map((valor, indice) => {
    const x = valores.length === 1 ? ancho / 2 : margen + (indice * (ancho - margen * 2)) / (valores.length - 1);
    const y = tope > 0 ? base - (Math.max(0, valor) / tope) * util : base;
    return { x: redondear(x), y: redondear(y) };
  });
}

// Atributo points de un <polyline>
export function puntosLinea(
  serie: number[],
  ancho: number,
  alto: number,
  margen = 0,
  maximo?: number,
) {
  return coordenadasLinea(serie, ancho, alto, margen, maximo)
    .map(({ x, y }) => `${x},${y}`)
    .join(" ");
}

// Marcas "redondas" del eje Y, de 0 a un tope >= maximo (p. ej. 0, 5, 10, 15)
export function marcasEje(maximo: number, cantidad = 4) {
  if (!(maximo > 0)) return [0, 1];
  const crudo = maximo / cantidad;
  const potencia = 10 ** Math.floor(Math.log10(crudo));
  const paso = [1, 2, 5, 10].map((factor) => factor * potencia).find((opcion) => opcion >= crudo) ?? crudo;
  const pasoFinal = Math.max(1, paso);
  const marcas: number[] = [];
  for (let valor = 0; valor < maximo + pasoFinal; valor += pasoFinal) marcas.push(valor);
  return marcas;
}

export function porcentaje(cantidad: number, total: number) {
  if (!(total > 0)) return "0 %";
  return `${Math.round((cantidad / total) * 100)} %`;
}

export function formatoNumero(valor: number, decimales = 0) {
  return valor.toLocaleString("es-UY", { maximumFractionDigits: decimales });
}

const MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

// "2025-03" → "mar 2025"; un año u otro texto queda igual
export function etiquetaPeriodo(periodo: string) {
  const mes = /^(\d{4})-(\d{2})$/.exec(periodo);
  if (!mes) return periodo;
  const indice = Number(mes[2]) - 1;
  return MESES_CORTOS[indice] ? `${MESES_CORTOS[indice]} ${mes[1]}` : periodo;
}
