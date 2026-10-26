import { describe, expect, it } from "vitest";
import {
  SIN_DATOS,
  aCsv,
  aPdf,
  celdaCsv,
  esFormatoReporte,
  esVistaReporte,
  nombreArchivo,
  seccionesReporte,
  type Reporte,
} from "../lib/reportes";

const AHORA = new Date("2026-10-26T15:30:00Z"); // 12:30 en Montevideo

function reporteDe(filas: (string | number)[][], titulo = "Prueba"): Reporte {
  return {
    titulo,
    filtros: [{ etiqueta: "Organismo", valor: "ANII" }],
    generado: "26/10/2026, 12:30",
    secciones: [{ titulo: "Sección", columnas: ["Categoría", "Cantidad"], filas }],
  };
}

describe("aCsv", () => {
  it("empieza con BOM y usa CRLF", () => {
    const csv = aCsv(reporteDe([["a", 1]]));
    expect(csv.startsWith("﻿")).toBe(true);
    expect(csv.endsWith("\r\n")).toBe(true);
    expect(csv.replace(/\r\n/g, "")).not.toMatch(/\n|\r/);
  });

  it("encabezado con título, fecha y filtros; secciones separadas por línea vacía", () => {
    const lineas = aCsv(reporteDe([["a", 1]])).slice(1).split("\r\n");
    expect(lineas.slice(0, 7)).toEqual([
      "Prueba",
      "Generado;26/10/2026, 12:30",
      "Organismo;ANII",
      "",
      "Sección",
      "Categoría;Cantidad",
      "a;1",
    ]);
  });

  it("escapa comillas, separador y saltos de línea (RFC 4180)", () => {
    expect(celdaCsv('Dijo "hola"')).toBe('"Dijo ""hola"""');
    expect(celdaCsv("uno;dos")).toBe('"uno;dos"');
    expect(celdaCsv("línea 1\nlínea 2")).toBe('"línea 1\nlínea 2"');
    expect(celdaCsv("con\r\nCRLF")).toBe('"con\r\nCRLF"');
    expect(celdaCsv("simple, con coma")).toBe("simple, con coma");
  });

  it("neutraliza fórmulas en textos", () => {
    expect(celdaCsv("=SUMA(A1:A2)")).toBe("'=SUMA(A1:A2)");
    expect(celdaCsv("+598")).toBe("'+598");
    expect(celdaCsv("-3")).toBe("'-3");
    expect(celdaCsv("@usuario")).toBe("'@usuario");
    expect(celdaCsv("\tTab")).toBe("'\tTab");
    // Fórmula con separador: se neutraliza y además va entre comillas
    expect(celdaCsv('=HIPERVINCULO("x";"y")')).toBe('"\'=HIPERVINCULO(""x"";""y"")"');
  });

  it("los números negativos no reciben apóstrofo y los decimales usan coma", () => {
    expect(celdaCsv(-3)).toBe("-3");
    expect(celdaCsv(1.5)).toBe("1,5");
    expect(celdaCsv(0)).toBe("0");
    expect(aCsv(reporteDe([["Saldo", -3]]))).toContain("\r\nSaldo;-3\r\n");
  });

  it("neutraliza también los filtros que vienen de la URL", () => {
    const reporte = reporteDe([]);
    reporte.filtros = [{ etiqueta: "Organismo", valor: "=cmd()" }];
    expect(aCsv(reporte)).toContain("Organismo;'=cmd()");
  });

  it("una sección sin filas escribe el aviso de sin datos", () => {
    expect(aCsv(reporteDe([]))).toContain(`Categoría;Cantidad\r\n${SIN_DATOS}\r\n`);
  });
});

describe("nombreArchivo", () => {
  it("usa vista, fecha AAAA-MM-DD y extensión", () => {
    expect(nombreArchivo("fondos", AHORA, "csv")).toBe("interfascia-analisis-fondos-2026-10-26.csv");
    expect(nombreArchivo("uso", AHORA, "pdf")).toBe("interfascia-analisis-uso-2026-10-26.pdf");
  });

  it("toma el día de Montevideo, no el de UTC", () => {
    // 01:00 UTC del 27 son las 22:00 del 26 en Montevideo
    expect(nombreArchivo("resumen", new Date("2026-10-27T01:00:00Z"), "csv")).toBe(
      "interfascia-analisis-resumen-2026-10-26.csv",
    );
  });
});

describe("validaciones", () => {
  it("vistas y formatos", () => {
    expect(esVistaReporte("uso")).toBe(true);
    expect(esVistaReporte("tendencias")).toBe(true);
    expect(esVistaReporte("otra")).toBe(false);
    expect(esFormatoReporte("pdf")).toBe(true);
    expect(esFormatoReporte("xlsx")).toBe(false);
  });
});

const FONDOS = {
  disponible: true,
  filtros_aplicados: ["organismo"],
  total: 5,
  por_organismo: [
    { etiqueta: "ANII", cantidad: 3 },
    { etiqueta: "INIA", cantidad: 2 },
  ],
  por_tematica: [{ etiqueta: "Salud", cantidad: 5 }],
  por_estado: [],
  por_anio_apertura: [{ etiqueta: "2025", cantidad: 5 }],
  por_sector_economico: { disponible: false, motivo: "Sin sector económico." },
  financiamiento: { informado: 4, sin_informar: 1 },
  tematica_multiple: false,
};

describe("seccionesReporte", () => {
  it("fondos: indicadores, una sección por serie y el motivo de lo no disponible", () => {
    const reporte = seccionesReporte("fondos", FONDOS, { organismo: "ANII", desde: "2025-01-01" }, AHORA);
    expect(reporte.titulo).toBe("Análisis de datos: Fondos");
    expect(reporte.generado).toContain("26/10/2026");
    expect(reporte.filtros).toEqual([
      { etiqueta: "Organismo", valor: "ANII" },
      { etiqueta: "Período", valor: "desde 01/01/2025" },
      { etiqueta: "Nota", valor: "El filtro Período no aplica a fondos." },
    ]);
    expect(reporte.secciones.map((s) => s.titulo)).toEqual([
      "Indicadores",
      "Fondos por organismo",
      "Fondos por área temática",
      "Fondos por estado de convocatoria",
      "Fondos por año de apertura",
      "Fondos por sector económico",
    ]);
    const organismo = reporte.secciones[1];
    expect(organismo.columnas).toEqual(["Organismo", "Cantidad"]);
    expect(organismo.filas).toEqual([["ANII", 3], ["INIA", 2]]);
    expect(organismo.barras).toBe(true);
    expect(reporte.secciones[3].filas).toEqual([]);
    expect(reporte.secciones[5].filas).toEqual([["Sin sector económico."]]);
  });

  it("fondos no disponibles: una sola sección con el motivo", () => {
    const reporte = seccionesReporte("fondos", { disponible: false }, {}, AHORA);
    expect(reporte.secciones).toHaveLength(1);
    expect(reporte.secciones[0].filas[0][0]).toMatch(/No hay datos de fondos/);
    expect(reporte.filtros).toEqual([{ etiqueta: "Filtros", valor: "Sin filtros (todos los datos)" }]);
  });

  it("resumen: tabla Indicador/Valor por grupo y motivo si no hay datos", () => {
    const reporte = seccionesReporte(
      "resumen",
      {
        fondos: { disponible: true, total: 10, abiertos: 4, proximos: 1, cerrados: 5, cierran_30_dias: 2, organismos: 3, con_financiamiento: 7 },
        investigadores: { disponible: false, total: 0 },
        proyectos: { disponible: true, total: 2, en_curso: 1, finalizados: 1 },
        generado: "2026-10-26T12:00:00Z",
      },
      {},
      AHORA,
    );
    expect(reporte.secciones.map((s) => s.titulo)).toEqual(["Fondos", "Investigadores", "Proyectos"]);
    expect(reporte.secciones[0].columnas).toEqual(["Indicador", "Valor"]);
    expect(reporte.secciones[0].filas[0]).toEqual(["Fondos", 10]);
    expect(reporte.secciones[0].filas).toContainEqual(["Abiertos", 4]);
    expect(reporte.secciones[1].filas).toEqual([["No hay datos de investigadores cargados en la plataforma."]]);
    expect(reporte.secciones[2].filas).toContainEqual(["En curso", 1]);
  });

  it("investigadores: tolera series faltantes", () => {
    const reporte = seccionesReporte(
      "investigadores",
      { disponible: true, total: 3, lineas_investigacion: { total: 6, promedio_por_investigador: 2 }, por_institucion: [{ etiqueta: "UdelaR", cantidad: 3 }] },
      {},
      AHORA,
    );
    expect(reporte.secciones).toHaveLength(6);
    expect(reporte.secciones[0].filas).toContainEqual(["Líneas por investigador (promedio)", 2]);
    expect(reporte.secciones[1].filas).toEqual([["UdelaR", 3]]);
    expect(reporte.secciones[2].filas).toEqual([]);
  });

  it("proyectos: series y organismo no disponible", () => {
    const reporte = seccionesReporte(
      "proyectos",
      {
        disponible: true,
        total: 2,
        por_estado: [{ etiqueta: "En curso", cantidad: 2 }],
        por_anio: [],
        por_tematica: [],
        por_organismo: { disponible: false, motivo: "Los proyectos no registran organismo." },
      },
      {},
      AHORA,
    );
    expect(reporte.secciones.map((s) => s.titulo)).toEqual([
      "Indicadores",
      "Proyectos por estado",
      "Proyectos por año",
      "Proyectos por área temática",
      "Proyectos por organismo",
    ]);
    expect(reporte.secciones[4].filas).toEqual([["Los proyectos no registran organismo."]]);
  });

  it("tendencias: une apertura y cierre por período y respeta lo no disponible", () => {
    const reporte = seccionesReporte(
      "tendencias",
      {
        agrupar: "mes",
        fondos_por_apertura: [{ periodo: "2025-01", cantidad: 2 }, { periodo: "2025-03", cantidad: 1 }],
        fondos_por_cierre: [{ periodo: "2025-03", cantidad: 4 }],
        proyectos_por_anio: [],
        investigadores_incorporados: [],
        disponible: { fondos: true, proyectos: true, investigadores: false },
      },
      { agrupar: "mes" },
      AHORA,
    );
    const fondos = reporte.secciones[0];
    expect(fondos.columnas).toEqual(["Período", "Fondos por apertura", "Fondos por cierre"]);
    expect(fondos.filas).toEqual([
      ["ene 2025", 2, 0],
      ["mar 2025", 1, 4],
    ]);
    expect(reporte.secciones[1].filas).toEqual([]);
    expect(reporte.secciones[2].columnas).toEqual(["Motivo"]);
    expect(reporte.filtros).toContainEqual({ etiqueta: "Agrupación", valor: "Por mes" });
  });

  it("uso: indicadores, funcionalidad, días y usuarios registrados", () => {
    const reporte = seccionesReporte(
      "uso",
      {
        desde: "2026-09-26",
        hasta: "2026-10-26",
        total_eventos: 12,
        usuarios_distintos: 3,
        busquedas: 5,
        por_funcionalidad: [{ clave: "busqueda", etiqueta: "Búsqueda", cantidad: 5 }],
        por_dia: [{ periodo: "2026-10-25", cantidad: 0 }, { periodo: "2026-10-26", cantidad: 12 }],
        usuarios_registrados: {
          total: 8,
          por_estado: [{ etiqueta: "Habilitado", cantidad: 6 }],
          por_perfil: [],
        },
      },
      {},
      AHORA,
    );
    expect(reporte.titulo).toBe("Métricas de uso de la plataforma");
    expect(reporte.filtros).toEqual([{ etiqueta: "Período", valor: "26/09/2026 al 26/10/2026" }]);
    expect(reporte.secciones.map((s) => s.titulo)).toEqual([
      "Indicadores",
      "Uso por funcionalidad",
      "Actividad por día",
      "Usuarios registrados por estado",
      "Usuarios registrados por perfil",
    ]);
    expect(reporte.secciones[0].filas).toEqual([
      ["Total de eventos", 12],
      ["Usuarios distintos", 3],
      ["Búsquedas", 5],
      ["Usuarios registrados", 8],
    ]);
    expect(reporte.secciones[1].filas).toEqual([["Búsqueda", 5]]);
    expect(reporte.secciones[2].filas).toEqual([["25/10/2026", 0], ["26/10/2026", 12]]);
    expect(reporte.secciones[4].filas).toEqual([]);
  });

  it("uso con JSON vacío no rompe", () => {
    const reporte = seccionesReporte("uso", {}, {}, AHORA);
    expect(reporte.secciones[0].filas[0]).toEqual(["Total de eventos", 0]);
    expect(reporte.secciones.slice(1).every((s) => s.filas.length === 0)).toBe(true);
  });
});

describe("notas de filtros que no aplican", () => {
  const notas = (reporte: Reporte) => reporte.filtros.filter((f) => f.etiqueta === "Nota").map((f) => f.valor);
  const filtros = { organismo: "ANII", estado: "Abierta", tematica: "Salud" };

  it("tendencias: una nota por entidad con filtros que no aplican", () => {
    const reporte = seccionesReporte(
      "tendencias",
      {
        fondos_por_apertura: [],
        fondos_por_cierre: [],
        proyectos_por_anio: [],
        investigadores_incorporados: [],
        disponible: { fondos: true, proyectos: true, investigadores: true },
        filtros_aplicados: {
          fondos: ["organismo", "tematica", "estado", "periodo"],
          proyectos: ["tematica"],
          investigadores: [],
        },
      },
      filtros,
      AHORA,
    );
    expect(notas(reporte)).toEqual([
      "Los filtros Organismo y Estado no aplican a proyectos.",
      "Los filtros Organismo, Área temática y Estado no aplican a investigadores.",
    ]);
    // Sale en el CSV (encabezado) y el PDF se genera
    expect(aCsv(reporte)).toContain("Nota;Los filtros Organismo y Estado no aplican a proyectos.");
    expect(new TextDecoder().decode(new Uint8Array(aPdf(reporte)).slice(0, 5))).toBe("%PDF-");
  });

  it("tendencias sin filtros_aplicados o entidad no disponible: sin notas", () => {
    const base = { disponible: { fondos: true, proyectos: false, investigadores: true } };
    expect(notas(seccionesReporte("tendencias", base, filtros, AHORA))).toEqual([]);
    const conCampo = { ...base, filtros_aplicados: { fondos: ["organismo", "tematica", "estado"], proyectos: [], investigadores: ["organismo", "tematica", "estado"] } };
    expect(notas(seccionesReporte("tendencias", conCampo, filtros, AHORA))).toEqual([]);
  });

  it("sin filtros activos no hay notas", () => {
    expect(notas(seccionesReporte("proyectos", { disponible: true, filtros_aplicados: [] }, {}, AHORA))).toEqual([]);
  });

  it("fondos, investigadores y proyectos usan su filtros_aplicados", () => {
    expect(notas(seccionesReporte("proyectos", { disponible: true, filtros_aplicados: ["tematica"] }, filtros, AHORA))).toEqual([
      "Los filtros Organismo y Estado no aplican a proyectos.",
    ]);
    expect(notas(seccionesReporte("investigadores", { disponible: true, filtros_aplicados: ["organismo", "tematica"] }, filtros, AHORA))).toEqual([
      "El filtro Estado no aplica a investigadores.",
    ]);
    expect(notas(seccionesReporte("fondos", { disponible: true }, filtros, AHORA))).toEqual([]);
  });

  it("resumen: una nota por grupo, salvo los no disponibles", () => {
    const reporte = seccionesReporte(
      "resumen",
      {
        fondos: { disponible: true, filtros_aplicados: ["organismo", "tematica", "estado", "periodo"] },
        investigadores: { disponible: true, filtros_aplicados: ["organismo"] },
        proyectos: { disponible: false, filtros_aplicados: [] },
      },
      filtros,
      AHORA,
    );
    expect(notas(reporte)).toEqual(["Los filtros Área temática y Estado no aplican a investigadores."]);
  });
});

describe("aPdf", () => {
  it("genera un PDF aun con series vacías y no disponibles", () => {
    const reporte = seccionesReporte("fondos", FONDOS, {}, AHORA);
    const bytes = new Uint8Array(aPdf(reporte));
    expect(new TextDecoder().decode(bytes.slice(0, 5))).toBe("%PDF-");
  });
});
