import { describe, expect, it } from "vitest";
import {
  FILTROS_VACIOS,
  anchoBarra,
  avisoNoAplicados,
  coordenadasLinea,
  esFechaValida,
  etiquetaFiltro,
  etiquetaPeriodo,
  filtrosNoAplicados,
  hrefAnalisis,
  leerFiltros,
  marcasEje,
  porcentaje,
  puntosLinea,
  queryDeFiltros,
} from "../lib/analisis";

describe("leerFiltros", () => {
  it("sin parámetros devuelve los valores por defecto", () => {
    expect(leerFiltros({})).toEqual(FILTROS_VACIOS);
  });

  it("descarta fechas inválidas o con otro formato", () => {
    const filtros = leerFiltros({ desde: "2025-02-30", hasta: "15/03/2025" });
    expect(filtros.desde).toBe("");
    expect(filtros.hasta).toBe("");
  });

  it("acepta fechas válidas y da vuelta un rango invertido", () => {
    expect(leerFiltros({ desde: "2025-01-10", hasta: "2025-03-01" })).toMatchObject({ desde: "2025-01-10", hasta: "2025-03-01" });
    expect(leerFiltros({ desde: "2025-03-01", hasta: "2025-01-10" })).toMatchObject({ desde: "2025-01-10", hasta: "2025-03-01" });
  });

  it("descarta vistas, agrupaciones y estados desconocidos", () => {
    const filtros = leerFiltros({ vista: "admin", agrupar: "semana", estado: "Borrador" });
    expect(filtros.vista).toBe("resumen");
    expect(filtros.agrupar).toBe("anio");
    expect(filtros.estado).toBe("");
  });

  it("con parámetros repetidos usa el primero", () => {
    const filtros = leerFiltros({ vista: ["fondos", "proyectos"], organismo: [" ANII ", "INIA"], agrupar: ["mes"] });
    expect(filtros.vista).toBe("fondos");
    expect(filtros.organismo).toBe("ANII");
    expect(filtros.agrupar).toBe("mes");
  });

  it("acepta los estados del contrato, con tilde", () => {
    expect(leerFiltros({ estado: "Próxima" }).estado).toBe("Próxima");
  });
});

describe("esFechaValida", () => {
  it("valida años bisiestos", () => {
    expect(esFechaValida("2024-02-29")).toBe(true);
    expect(esFechaValida("2025-02-29")).toBe(false);
  });
});

describe("queryDeFiltros", () => {
  it("omite los vacíos", () => {
    expect(queryDeFiltros({ ...FILTROS_VACIOS })).toBe("");
    expect(queryDeFiltros({ ...FILTROS_VACIOS, organismo: "ANII", tematica: "  " })).toBe("organismo=ANII");
  });

  it("escapa caracteres especiales", () => {
    const query = queryDeFiltros({ organismo: "A&B = C", estado: "Próxima" });
    expect(query).toBe("organismo=A%26B+%3D+C&estado=Pr%C3%B3xima");
    expect(new URLSearchParams(query).get("organismo")).toBe("A&B = C");
  });

  it("suma los extras sin vacíos", () => {
    expect(queryDeFiltros({ desde: "2025-01-01" }, { agrupar: "mes", vista: undefined })).toBe("desde=2025-01-01&agrupar=mes");
  });
});

describe("hrefAnalisis", () => {
  it("no escribe la vista ni la agrupación por defecto", () => {
    expect(hrefAnalisis(FILTROS_VACIOS)).toBe("/analisis-datos");
  });

  it("conserva filtros al cambiar de vista y solo lleva agrupar en tendencias", () => {
    const filtros = { ...FILTROS_VACIOS, organismo: "ANII", agrupar: "mes" as const };
    expect(hrefAnalisis(filtros, { vista: "fondos" })).toBe("/analisis-datos?organismo=ANII&vista=fondos");
    expect(hrefAnalisis(filtros, { vista: "tendencias" })).toBe("/analisis-datos?organismo=ANII&vista=tendencias&agrupar=mes");
  });
});

describe("anchoBarra", () => {
  it("con máximo 0 devuelve 0", () => {
    expect(anchoBarra(0, 0)).toBe(0);
    expect(anchoBarra(5, 0)).toBe(0);
  });

  it("es proporcional al máximo y no pasa de 100", () => {
    expect(anchoBarra(10, 10)).toBe(100);
    expect(anchoBarra(5, 10)).toBe(50);
    expect(anchoBarra(0, 10)).toBe(0);
    expect(anchoBarra(20, 10)).toBe(100);
    expect(anchoBarra(-3, 10)).toBe(0);
  });
});

describe("puntosLinea", () => {
  it("un solo punto queda centrado", () => {
    expect(puntosLinea([4], 100, 50)).toBe("50,0");
  });

  it("todo en 0 queda en la base", () => {
    expect(puntosLinea([0, 0, 0], 100, 50, 5)).toBe("5,45 50,45 95,45");
  });

  it("reparte los puntos a lo ancho y escala al máximo", () => {
    expect(puntosLinea([0, 5, 10], 100, 50)).toBe("0,50 50,25 100,0");
  });

  it("con un máximo compartido dos series usan la misma escala", () => {
    expect(puntosLinea([5, 5], 100, 100, 0, 10)).toBe("0,50 100,50");
    expect(coordenadasLinea([10], 100, 100, 0, 20)).toEqual([{ x: 50, y: 50 }]);
  });

  it("serie vacía devuelve texto vacío", () => {
    expect(puntosLinea([], 100, 50)).toBe("");
  });
});

describe("marcasEje", () => {
  it("cubre el máximo con pasos redondos", () => {
    expect(marcasEje(10)).toEqual([0, 5, 10]);
    expect(marcasEje(7)).toEqual([0, 2, 4, 6, 8]);
    expect(marcasEje(1)).toEqual([0, 1]);
  });

  it("sin datos devuelve una escala mínima", () => {
    expect(marcasEje(0)).toEqual([0, 1]);
  });
});

describe("porcentaje", () => {
  it("con total 0 devuelve 0 %", () => {
    expect(porcentaje(5, 0)).toBe("0 %");
  });

  it("redondea al entero", () => {
    expect(porcentaje(1, 3)).toBe("33 %");
    expect(porcentaje(2, 2)).toBe("100 %");
  });
});

describe("filtrosNoAplicados", () => {
  it("devuelve las etiquetas de los activos que la sección no usa", () => {
    const filtros = { ...FILTROS_VACIOS, organismo: "ANII", estado: "Abierta", desde: "2025-01-01" };
    expect(filtrosNoAplicados(filtros, ["organismo"])).toEqual(["Estado", "Período"]);
  });

  it("sin filtros activos no avisa nada", () => {
    expect(filtrosNoAplicados(FILTROS_VACIOS, [])).toEqual([]);
  });

  it("arma el texto del aviso en singular y plural", () => {
    expect(avisoNoAplicados([])).toBeNull();
    expect(avisoNoAplicados(["Estado"])).toBe("El filtro Estado no aplica a esta sección.");
    expect(avisoNoAplicados(["Organismo", "Estado", "Período"])).toBe(
      "Los filtros Organismo, Estado y Período no aplican a esta sección.",
    );
  });
});

describe("etiquetas", () => {
  it("traduce las claves de filtro", () => {
    expect(etiquetaFiltro("tematica")).toBe("Área temática");
    expect(etiquetaFiltro("periodo")).toBe("Período");
    expect(etiquetaFiltro("otra")).toBe("otra");
  });

  it("formatea períodos mensuales", () => {
    expect(etiquetaPeriodo("2025-03")).toBe("mar 2025");
    expect(etiquetaPeriodo("2025")).toBe("2025");
  });
});
