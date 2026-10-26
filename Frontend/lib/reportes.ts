// Exportación de reportes del análisis de datos (RF006-07) y de las métricas de uso (RF006-08).
// seccionesReporte arma un Reporte neutro (título, filtros, tablas) a partir del JSON de la API;
// aCsv y aPdf lo convierten al archivo. Sin dependencias de sesión: lo usan la ruta de
// exportación y los tests.

import { jsPDF } from "jspdf";
import {
  ETIQUETAS_VISTA,
  VISTAS,
  esFechaValida,
  etiquetaPeriodo,
  filtrosNoAplicados,
  formatoNumero,
  type Filtros,
  type PuntoTiempo,
  type Serie,
} from "./analisis";

// ============================================================
// CONTRATO DE /api/admin/analisis/uso
// ============================================================

export type MetricasUso = {
  desde: string;
  hasta: string;
  total_eventos: number;
  usuarios_distintos: number;
  busquedas: number;
  por_funcionalidad: { clave: string; etiqueta: string; cantidad: number }[];
  por_dia: PuntoTiempo[];
  usuarios_registrados: {
    total: number;
    por_estado: Serie;
    por_perfil: Serie;
  };
};

// ============================================================
// REPORTE
// ============================================================

export const VISTAS_REPORTE = [...VISTAS, "uso"] as const;
export type VistaReporte = (typeof VISTAS_REPORTE)[number];

export const FORMATOS_REPORTE = ["csv", "pdf"] as const;
export type FormatoReporte = (typeof FORMATOS_REPORTE)[number];

export type Celda = string | number;

export type SeccionReporte = {
  titulo: string;
  columnas: string[];
  filas: Celda[][];
  // Serie etiqueta/cantidad: en el PDF se dibuja además como barras
  barras?: boolean;
};

export type Reporte = {
  titulo: string;
  filtros: { etiqueta: string; valor: string }[];
  generado: string;
  secciones: SeccionReporte[];
};

export const SIN_DATOS = "No hay datos para estos filtros.";

export function esVistaReporte(valor: string): valor is VistaReporte {
  return (VISTAS_REPORTE as readonly string[]).includes(valor);
}

export function esFormatoReporte(valor: string): valor is FormatoReporte {
  return (FORMATOS_REPORTE as readonly string[]).includes(valor);
}

// "2025-03-15" → "15/03/2025"
export function fechaCorta(iso: string) {
  if (!esFechaValida(iso)) return iso;
  const [anio, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${anio}`;
}

// Fecha y hora de Montevideo, sin depender de la zona del servidor
export function formatoGenerado(fecha: Date) {
  return new Intl.DateTimeFormat("es-UY", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: "America/Montevideo",
  }).format(fecha);
}

// ---- Lectura tolerante del JSON (lo que falte se toma como vacío) ----

type Objeto = Record<string, unknown>;

function objeto(valor: unknown): Objeto {
  return valor && typeof valor === "object" && !Array.isArray(valor) ? (valor as Objeto) : {};
}

function numero(valor: unknown) {
  return typeof valor === "number" && Number.isFinite(valor) ? valor : 0;
}

function lista(valor: unknown): Objeto[] {
  return Array.isArray(valor) ? valor.map(objeto) : [];
}

function serie(valor: unknown): Serie {
  return lista(valor).map((item) => ({ etiqueta: String(item.etiqueta ?? ""), cantidad: numero(item.cantidad) }));
}

function puntos(valor: unknown): PuntoTiempo[] {
  return lista(valor).map((item) => ({ periodo: String(item.periodo ?? ""), cantidad: numero(item.cantidad) }));
}

// ---- Constructores de secciones ----

function seccionMotivo(titulo: string, motivo: string): SeccionReporte {
  return { titulo, columnas: ["Motivo"], filas: [[motivo]] };
}

function seccionSerie(titulo: string, columna: string, datos: unknown): SeccionReporte {
  return {
    titulo,
    columnas: [columna, "Cantidad"],
    filas: serie(datos).map((item) => [item.etiqueta, item.cantidad]),
    barras: true,
  };
}

function seccionIndicadores(titulo: string, indicadores: [string, number][]): SeccionReporte {
  return { titulo, columnas: ["Indicador", "Valor"], filas: indicadores };
}

// Varias series de tiempo en una tabla: una fila por período, ordenadas
function seccionTiempo(titulo: string, series: { nombre: string; puntos: unknown }[]): SeccionReporte {
  const mapas = series.map((item) => new Map(puntos(item.puntos).map((punto) => [punto.periodo, punto.cantidad])));
  const periodos = Array.from(new Set(mapas.flatMap((mapa) => Array.from(mapa.keys())))).sort();
  return {
    titulo,
    columnas: ["Período", ...series.map((item) => item.nombre)],
    filas: periodos.map((periodo) => [etiquetaPeriodo(periodo), ...mapas.map((mapa) => mapa.get(periodo) ?? 0)]),
  };
}

function motivoDe(valor: unknown, porDefecto: string) {
  const motivo = objeto(valor).motivo;
  return typeof motivo === "string" && motivo ? motivo : porDefecto;
}

const MOTIVO_SIN_FUENTE = "La plataforma todavía no registra este dato.";

function seccionesResumen(datos: Objeto): SeccionReporte[] {
  const fondos = objeto(datos.fondos);
  const investigadores = objeto(datos.investigadores);
  const proyectos = objeto(datos.proyectos);

  const grupo = (titulo: string, entidad: string, seccion: Objeto, indicadores: [string, number][]) =>
    seccion.disponible === false
      ? seccionMotivo(titulo, `No hay datos de ${entidad} cargados en la plataforma.`)
      : seccionIndicadores(titulo, indicadores);

  return [
    grupo("Fondos", "fondos", fondos, [
      ["Fondos", numero(fondos.total)],
      ["Abiertos", numero(fondos.abiertos)],
      ["Próximos a abrir", numero(fondos.proximos)],
      ["Cerrados", numero(fondos.cerrados)],
      ["Cierran en los próximos 30 días", numero(fondos.cierran_30_dias)],
      ["Organismos financiadores", numero(fondos.organismos)],
      ["Con financiamiento informado", numero(fondos.con_financiamiento)],
    ]),
    grupo("Investigadores", "investigadores", investigadores, [
      ["Investigadores", numero(investigadores.total)],
      ["Instituciones", numero(investigadores.instituciones)],
      ["Con nivel SNI", numero(investigadores.con_nivel_sni)],
    ]),
    grupo("Proyectos", "proyectos", proyectos, [
      ["Proyectos", numero(proyectos.total)],
      ["En curso", numero(proyectos.en_curso)],
      ["Finalizados", numero(proyectos.finalizados)],
    ]),
  ];
}

function seccionesFondos(datos: Objeto): SeccionReporte[] {
  if (datos.disponible === false) {
    return [seccionMotivo("Fondos", "No hay datos de fondos cargados en la plataforma.")];
  }
  const financiamiento = objeto(datos.financiamiento);
  return [
    seccionIndicadores("Indicadores", [
      ["Fondos", numero(datos.total)],
      ["Con financiamiento informado", numero(financiamiento.informado)],
      ["Sin financiamiento informado", numero(financiamiento.sin_informar)],
    ]),
    seccionSerie("Fondos por organismo", "Organismo", datos.por_organismo),
    seccionSerie("Fondos por área temática", "Área temática", datos.por_tematica),
    seccionSerie("Fondos por estado de convocatoria", "Estado", datos.por_estado),
    seccionSerie("Fondos por año de apertura", "Año", datos.por_anio_apertura),
    seccionMotivo("Fondos por sector económico", motivoDe(datos.por_sector_economico, MOTIVO_SIN_FUENTE)),
  ];
}

function seccionesInvestigadores(datos: Objeto): SeccionReporte[] {
  if (datos.disponible === false) {
    return [seccionMotivo("Investigadores", "No hay datos de investigadores cargados en la plataforma.")];
  }
  const lineas = objeto(datos.lineas_investigacion);
  return [
    seccionIndicadores("Indicadores", [
      ["Investigadores", numero(datos.total)],
      ["Líneas de investigación", numero(lineas.total)],
      ["Líneas por investigador (promedio)", numero(lineas.promedio_por_investigador)],
    ]),
    seccionSerie("Investigadores por institución", "Institución", datos.por_institucion),
    seccionSerie("Investigadores por área temática", "Área temática", datos.por_area_tematica),
    seccionSerie("Investigadores por nivel SNI", "Nivel SNI", datos.por_nivel_sni),
    seccionSerie("Investigadores por categoría SNI", "Categoría SNI", datos.por_categoria_sni),
    seccionSerie("Investigadores por formación", "Formación", datos.por_formacion),
  ];
}

function seccionesProyectos(datos: Objeto): SeccionReporte[] {
  if (datos.disponible === false) {
    return [seccionMotivo("Proyectos", "No hay datos de proyectos cargados en la plataforma.")];
  }
  return [
    seccionIndicadores("Indicadores", [["Proyectos", numero(datos.total)]]),
    seccionSerie("Proyectos por estado", "Estado", datos.por_estado),
    seccionSerie("Proyectos por año", "Año", datos.por_anio),
    seccionSerie("Proyectos por área temática", "Área temática", datos.por_tematica),
    seccionMotivo("Proyectos por organismo", motivoDe(datos.por_organismo, MOTIVO_SIN_FUENTE)),
  ];
}

function seccionesTendencias(datos: Objeto): SeccionReporte[] {
  const disponible = objeto(datos.disponible);
  return [
    disponible.fondos === false
      ? seccionMotivo("Fondos por fecha de apertura y de cierre", "No hay datos de fondos cargados en la plataforma.")
      : seccionTiempo("Fondos por fecha de apertura y de cierre", [
          { nombre: "Fondos por apertura", puntos: datos.fondos_por_apertura },
          { nombre: "Fondos por cierre", puntos: datos.fondos_por_cierre },
        ]),
    disponible.proyectos === false
      ? seccionMotivo("Proyectos por año", "No hay datos de proyectos cargados en la plataforma.")
      : seccionTiempo("Proyectos por año", [{ nombre: "Proyectos", puntos: datos.proyectos_por_anio }]),
    disponible.investigadores === false
      ? seccionMotivo(
          "Investigadores incorporados a Interfascia (fecha de carga)",
          "No hay datos de investigadores cargados en la plataforma.",
        )
      : seccionTiempo("Investigadores incorporados a Interfascia (fecha de carga)", [
          { nombre: "Investigadores", puntos: datos.investigadores_incorporados },
        ]),
  ];
}

function seccionesUso(datos: Objeto): SeccionReporte[] {
  const registrados = objeto(datos.usuarios_registrados);
  return [
    seccionIndicadores("Indicadores", [
      ["Total de eventos", numero(datos.total_eventos)],
      ["Usuarios distintos", numero(datos.usuarios_distintos)],
      ["Búsquedas", numero(datos.busquedas)],
      ["Usuarios registrados", numero(registrados.total)],
    ]),
    seccionSerie("Uso por funcionalidad", "Funcionalidad", datos.por_funcionalidad),
    {
      titulo: "Actividad por día",
      columnas: ["Día", "Eventos"],
      filas: puntos(datos.por_dia).map((punto) => [fechaCorta(punto.periodo), punto.cantidad]),
    },
    seccionSerie("Usuarios registrados por estado", "Estado", registrados.por_estado),
    seccionSerie("Usuarios registrados por perfil", "Perfil", registrados.por_perfil),
  ];
}

// Filtros que se aplicaron, en texto para el encabezado del reporte
function filtrosReporte(vista: VistaReporte, datos: Objeto, filtros: Partial<Filtros>) {
  const salida: { etiqueta: string; valor: string }[] = [];

  if (vista === "uso") {
    // El rango efectivo lo decide la API (por defecto, los últimos 30 días)
    const desde = typeof datos.desde === "string" ? datos.desde : filtros.desde ?? "";
    const hasta = typeof datos.hasta === "string" ? datos.hasta : filtros.hasta ?? "";
    if (desde || hasta) salida.push({ etiqueta: "Período", valor: `${fechaCorta(desde)} al ${fechaCorta(hasta)}` });
    return salida;
  }

  if (filtros.organismo) salida.push({ etiqueta: "Organismo", valor: filtros.organismo });
  if (filtros.tematica) salida.push({ etiqueta: "Área temática", valor: filtros.tematica });
  if (filtros.estado) salida.push({ etiqueta: "Estado", valor: filtros.estado });
  if (filtros.desde || filtros.hasta) {
    const valor =
      filtros.desde && filtros.hasta
        ? `${fechaCorta(filtros.desde)} al ${fechaCorta(filtros.hasta)}`
        : filtros.desde
          ? `desde ${fechaCorta(filtros.desde)}`
          : `hasta ${fechaCorta(filtros.hasta ?? "")}`;
    salida.push({ etiqueta: "Período", valor });
  }
  if (salida.length === 0) salida.push({ etiqueta: "Filtros", valor: "Sin filtros (todos los datos)" });
  if (vista === "tendencias") {
    const agrupar = datos.agrupar ?? filtros.agrupar;
    salida.push({ etiqueta: "Agrupación", valor: agrupar === "mes" ? "Por mes" : "Por año" });
  }
  for (const nota of notasNoAplicados(vista, datos, filtros)) salida.push({ etiqueta: "Nota", valor: nota });
  return salida;
}

// Aplicados de una sección; null si la API no los mandó (entonces no se avisa nada)
function aplicadosDe(valor: unknown): string[] | null {
  return Array.isArray(valor) ? valor.filter((clave): clave is string => typeof clave === "string") : null;
}

// "Los filtros Organismo y Estado no aplican a proyectos." por cada entidad afectada
export function notasNoAplicados(vista: VistaReporte, datos: Objeto, filtros: Partial<Filtros>) {
  const entidades: { entidad: string; aplicados: string[] | null }[] = [];
  const porEntidad = (fuente: (entidad: string) => unknown) =>
    ["fondos", "investigadores", "proyectos"].forEach((entidad) => {
      // Sin datos de la entidad el reporte ya lo dice; no hace falta avisar de filtros
      if (objeto(fuente(entidad)).disponible === false) return;
      entidades.push({ entidad, aplicados: aplicadosDe(objeto(fuente(entidad)).filtros_aplicados) });
    });

  if (vista === "resumen") {
    porEntidad((entidad) => datos[entidad]);
  } else if (vista === "tendencias") {
    const aplicados = objeto(datos.filtros_aplicados);
    const disponible = objeto(datos.disponible);
    for (const entidad of ["fondos", "proyectos", "investigadores"]) {
      if (disponible[entidad] === false) continue;
      entidades.push({ entidad, aplicados: aplicadosDe(aplicados[entidad]) });
    }
  } else if (vista !== "uso" && datos.disponible !== false) {
    entidades.push({ entidad: vista, aplicados: aplicadosDe(datos.filtros_aplicados) });
  }

  return entidades.flatMap(({ entidad, aplicados }) => {
    if (!aplicados) return [];
    const etiquetas = filtrosNoAplicados(filtros, aplicados);
    if (etiquetas.length === 0) return [];
    if (etiquetas.length === 1) return [`El filtro ${etiquetas[0]} no aplica a ${entidad}.`];
    const lista = `${etiquetas.slice(0, -1).join(", ")} y ${etiquetas[etiquetas.length - 1]}`;
    return [`Los filtros ${lista} no aplican a ${entidad}.`];
  });
}

export function seccionesReporte(
  vista: VistaReporte,
  datos: unknown,
  filtros: Partial<Filtros> = {},
  ahora: Date = new Date(),
): Reporte {
  const json = objeto(datos);
  const constructores: Record<VistaReporte, (datos: Objeto) => SeccionReporte[]> = {
    resumen: seccionesResumen,
    fondos: seccionesFondos,
    investigadores: seccionesInvestigadores,
    proyectos: seccionesProyectos,
    tendencias: seccionesTendencias,
    uso: seccionesUso,
  };

  return {
    titulo: vista === "uso" ? "Métricas de uso de la plataforma" : `Análisis de datos: ${ETIQUETAS_VISTA[vista]}`,
    filtros: filtrosReporte(vista, json, filtros),
    generado: formatoGenerado(ahora),
    secciones: constructores[vista](json),
  };
}

// "interfascia-analisis-fondos-2026-10-26.csv" (fecha de Montevideo)
export function nombreArchivo(vista: VistaReporte, fecha: Date, ext: string) {
  // en-CA formatea como AAAA-MM-DD
  const dia = new Intl.DateTimeFormat("en-CA", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    timeZone: "America/Montevideo",
  }).format(fecha);
  return `interfascia-analisis-${vista}-${dia}.${ext}`;
}

// ============================================================
// CSV
// ============================================================

// Separador ";": Excel con configuración regional en español (coma decimal) abre así el
// archivo en columnas con doble click; con "," lo dejaría todo en una sola columna.
// Por lo mismo, los decimales se escriben con coma.
const SEPARADOR = ";";
const FIN_LINEA = "\r\n";

// Texto que una planilla interpretaría como fórmula (inyección de CSV)
const INICIO_FORMULA = /^[=+\-@\t\r]/;

export function celdaCsv(valor: Celda) {
  let texto: string;
  if (typeof valor === "number") {
    // Los números van tal cual (un -3 es un número, no una fórmula)
    texto = Number.isFinite(valor) ? String(valor).replace(".", ",") : "";
  } else {
    texto = INICIO_FORMULA.test(valor) ? `'${valor}` : valor;
  }
  // RFC 4180: entre comillas si tiene separador, comillas o saltos; las comillas se duplican
  if (/[";\r\n]/.test(texto)) texto = `"${texto.replace(/"/g, '""')}"`;
  return texto;
}

function filaCsv(celdas: Celda[]) {
  return celdas.map(celdaCsv).join(SEPARADOR);
}

export function aCsv(reporte: Reporte) {
  const lineas: string[] = [
    filaCsv([reporte.titulo]),
    filaCsv(["Generado", reporte.generado]),
    ...reporte.filtros.map((filtro) => filaCsv([filtro.etiqueta, filtro.valor])),
  ];

  for (const seccion of reporte.secciones) {
    lineas.push("", filaCsv([seccion.titulo]), filaCsv(seccion.columnas));
    if (seccion.filas.length === 0) lineas.push(filaCsv([SIN_DATOS]));
    for (const fila of seccion.filas) lineas.push(filaCsv(fila));
  }

  // BOM: sin él Excel abre el UTF-8 como ANSI y rompe las tildes
  return `﻿${lineas.join(FIN_LINEA)}${FIN_LINEA}`;
}

// ============================================================
// PDF
// ============================================================

// Paleta del sitio (igual que el PDF del consultor IA) y color de la serie de los gráficos
const TINTA: [number, number, number] = [16, 42, 60];
const TEXTO_SUAVE: [number, number, number] = [96, 116, 130];
const CELESTE: [number, number, number] = [0, 119, 163];
const BORDE: [number, number, number] = [204, 236, 249];
const SERIE_1: [number, number, number] = [42, 120, 214]; // #2a78d6

const MARGEN = 48;
const ANCHO_PAGINA = 595.28; // A4 en puntos
const ALTO_PAGINA = 841.89;
const ANCHO_TEXTO = ANCHO_PAGINA - MARGEN * 2;
const ALTO_FILA = 16;
const ANCHO_COLUMNA_NUMERO = 110;
const ANCHO_ETIQUETA_BARRA = 170;
const ALTO_BARRA = 9;
// Igual que GraficoBarras: más categorías que esto quedan solo en la tabla
const MAXIMO_BARRAS = 12;

// Las fuentes estándar del PDF solo tienen caracteres latinos (WinAnsi): las tildes y la ñ
// están, pero comillas tipográficas, rayas y otros símbolos se reemplazan o se sacan
function limpiar(texto: string) {
  return texto
    .replace(/[‘’]/g, "'")
    .replace(/[“”]/g, '"')
    .replace(/[–—]/g, "-")
    .replace(/…/g, "...")
    .replace(/•/g, "-")
    .replace(/ /g, " ")
    .replace(/[^\x09\x0A\x0D\x20-\x7E\xA0-\xFF]/g, "");
}

function textoCelda(valor: Celda) {
  return typeof valor === "number" ? formatoNumero(valor, 2) : limpiar(valor);
}

export function aPdf(reporte: Reporte): ArrayBuffer {
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  let y = MARGEN;

  function asegurarEspacio(alto: number) {
    if (y + alto > ALTO_PAGINA - MARGEN) {
      doc.addPage();
      y = MARGEN;
      return true;
    }
    return false;
  }

  // Encabezado
  doc.setFont("helvetica", "bold");
  doc.setFontSize(9);
  doc.setTextColor(...CELESTE);
  doc.text("INTERFASCIA · ANÁLISIS DE DATOS", MARGEN, y);
  y += 22;

  doc.setFontSize(20);
  doc.setTextColor(...TINTA);
  const lineasTitulo = doc.splitTextToSize(limpiar(reporte.titulo), ANCHO_TEXTO) as string[];
  doc.text(lineasTitulo, MARGEN, y);
  y += lineasTitulo.length * 22;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(9.5);
  doc.setTextColor(...TEXTO_SUAVE);
  doc.text(limpiar(`Generado el ${reporte.generado}`), MARGEN, y);
  y += 14;
  for (const filtro of reporte.filtros) {
    const lineas = doc.splitTextToSize(limpiar(`${filtro.etiqueta}: ${filtro.valor}`), ANCHO_TEXTO) as string[];
    doc.text(lineas, MARGEN, y);
    y += lineas.length * 12;
  }
  y += 10;

  for (const seccion of reporte.secciones) {
    asegurarEspacio(70);

    doc.setDrawColor(...BORDE);
    doc.setLineWidth(1);
    doc.line(MARGEN, y, MARGEN + ANCHO_TEXTO, y);
    y += 20;

    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    doc.setTextColor(...TINTA);
    doc.text(limpiar(seccion.titulo), MARGEN, y);
    y += 18;

    // Sin datos o no disponible: una línea de texto en lugar de la tabla
    if (seccion.filas.length === 0 || seccion.columnas.length === 1) {
      const texto = seccion.filas.length === 0 ? SIN_DATOS : seccion.filas.map((fila) => String(fila[0])).join(" ");
      doc.setFont("helvetica", "italic");
      doc.setFontSize(10);
      doc.setTextColor(...TEXTO_SUAVE);
      const lineas = doc.splitTextToSize(limpiar(texto), ANCHO_TEXTO) as string[];
      asegurarEspacio(lineas.length * 13);
      doc.text(lineas, MARGEN, y);
      y += lineas.length * 13 + 10;
      continue;
    }

    if (seccion.barras) dibujarBarras(seccion);
    dibujarTabla(seccion);
    y += 10;
  }

  // Barras horizontales: etiqueta a la izquierda, barra y el valor al final
  function dibujarBarras(seccion: SeccionReporte) {
    const filas = seccion.filas.slice(0, MAXIMO_BARRAS);
    const maximo = Math.max(0, ...filas.map((fila) => (typeof fila[1] === "number" ? fila[1] : 0)));
    if (!(maximo > 0)) return;
    const anchoUtil = ANCHO_TEXTO - ANCHO_ETIQUETA_BARRA - 60;

    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    for (const fila of filas) {
      asegurarEspacio(ALTO_FILA);
      const cantidad = typeof fila[1] === "number" ? fila[1] : 0;
      const etiqueta = doc.splitTextToSize(textoCelda(fila[0]), ANCHO_ETIQUETA_BARRA - 8)[0] as string;
      const ancho = cantidad > 0 ? Math.max(1, (cantidad / maximo) * anchoUtil) : 0;
      const x = MARGEN + ANCHO_ETIQUETA_BARRA;

      doc.setTextColor(...TINTA);
      doc.text(etiqueta ?? "", MARGEN, y + 9);
      if (ancho > 0) {
        doc.setFillColor(...SERIE_1);
        doc.rect(x, y + 2, ancho, ALTO_BARRA, "F");
      }
      doc.text(textoCelda(cantidad), x + ancho + 4, y + 9);
      y += ALTO_FILA;
    }
    if (seccion.filas.length > MAXIMO_BARRAS) {
      doc.setFontSize(8);
      doc.setTextColor(...TEXTO_SUAVE);
      doc.text(
        `Se muestran las ${MAXIMO_BARRAS} primeras; las otras ${seccion.filas.length - MAXIMO_BARRAS} están en la tabla.`,
        MARGEN,
        y + 8,
      );
      y += 12;
    }
    y += 12;
  }

  // Tabla simple: la primera columna es texto y se parte en líneas; el resto son números a la derecha
  function dibujarTabla(seccion: SeccionReporte) {
    const otras = seccion.columnas.length - 1;
    const anchoNumero = Math.min(ANCHO_COLUMNA_NUMERO, (ANCHO_TEXTO * 0.6) / Math.max(1, otras));
    const anchoPrimera = ANCHO_TEXTO - anchoNumero * otras;

    function encabezado() {
      doc.setFont("helvetica", "bold");
      doc.setFontSize(9);
      doc.setTextColor(...TEXTO_SUAVE);
      seccion.columnas.forEach((columna, indice) => {
        const texto = limpiar(columna);
        if (indice === 0) doc.text(texto, MARGEN, y + 10);
        else doc.text(texto, MARGEN + anchoPrimera + anchoNumero * indice, y + 10, { align: "right" });
      });
      y += ALTO_FILA;
      doc.setDrawColor(...TINTA);
      doc.setLineWidth(0.6);
      doc.line(MARGEN, y - 2, MARGEN + ANCHO_TEXTO, y - 2);
    }

    asegurarEspacio(ALTO_FILA * 2);
    encabezado();

    doc.setFontSize(9.5);
    for (const fila of seccion.filas) {
      doc.setFont("helvetica", "normal");
      const lineas = doc.splitTextToSize(textoCelda(fila[0] ?? ""), anchoPrimera - 8) as string[];
      const alto = Math.max(ALTO_FILA, lineas.length * 12 + 4);
      // En una página nueva se repite el encabezado de la tabla
      if (asegurarEspacio(alto)) {
        encabezado();
        doc.setFont("helvetica", "normal");
      }

      doc.setFontSize(9.5);
      doc.setTextColor(...TINTA);
      doc.text(lineas, MARGEN, y + 10);
      fila.slice(1).forEach((valor, indice) => {
        doc.text(textoCelda(valor), MARGEN + anchoPrimera + anchoNumero * (indice + 1), y + 10, { align: "right" });
      });
      y += alto;
      doc.setDrawColor(...BORDE);
      doc.setLineWidth(0.5);
      doc.line(MARGEN, y - 2, MARGEN + ANCHO_TEXTO, y - 2);
    }
  }

  // Numeración de páginas
  const total = doc.getNumberOfPages();
  for (let pagina = 1; pagina <= total; pagina++) {
    doc.setPage(pagina);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.setTextColor(...TEXTO_SUAVE);
    doc.text(`${pagina} / ${total}`, ANCHO_PAGINA - MARGEN, ALTO_PAGINA - 24, { align: "right" });
  }

  return doc.output("arraybuffer");
}
