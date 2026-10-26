import { describe, expect, it } from "vitest";
import {
  agruparSuscripciones,
  diasRestantes,
  etiquetaTipo,
  filasCambios,
  validarDias,
  valorLegible,
  type Suscripcion,
} from "../lib/alertas";

describe("etiquetaTipo", () => {
  it("traduce los tipos conocidos", () => {
    expect(etiquetaTipo("apertura")).toBe("Apertura");
    expect(etiquetaTipo("cierre")).toBe("Próximo cierre");
    expect(etiquetaTipo("actualizacion")).toBe("Actualización");
  });

  it("deja tal cual un tipo desconocido", () => {
    expect(etiquetaTipo("otro")).toBe("otro");
  });
});

describe("filasCambios", () => {
  it("traduce los campos y muestra — para los vacíos", () => {
    const filas = filasCambios([
      { campo: "fecha_cierre", antes: "2026-11-01", despues: "2026-11-15" },
      { campo: "descripcion", antes: null, despues: "Nueva" },
      { campo: "monto_extra", antes: 10, despues: 20 },
    ]);
    expect(filas).toEqual([
      { campo: "Fecha de cierre", antes: "01/11/2026", despues: "15/11/2026" },
      { campo: "Descripción", antes: "—", despues: "Nueva" },
      { campo: "monto_extra", antes: "10", despues: "20" },
    ]);
  });

  it("devuelve lista vacía con detalle null", () => {
    expect(filasCambios(null)).toEqual([]);
    expect(filasCambios(undefined)).toEqual([]);
  });

  it("ignora un detalle mal formado", () => {
    expect(filasCambios({ dias_restantes: 3 })).toEqual([]);
    expect(filasCambios("texto")).toEqual([]);
    expect(filasCambios([null, 5, { antes: "a" }, { campo: "estado", despues: "cerrada" }])).toEqual([
      { campo: "Estado", antes: "—", despues: "cerrada" },
    ]);
  });
});

describe("valorLegible", () => {
  it("muestra las fechas ISO como dd/mm/aaaa", () => {
    expect(valorLegible("2026-11-01")).toBe("01/11/2026");
    // Solo fechas exactas: un texto que empieza con una fecha queda igual
    expect(valorLegible("2026-11-01 en Montevideo")).toBe("2026-11-01 en Montevideo");
  });

  it("recorta los textos largos a 200 caracteres con …", () => {
    const largo = valorLegible("a".repeat(500));
    expect(largo).toHaveLength(200);
    expect(largo.endsWith("…")).toBe(true);
    expect(valorLegible("b".repeat(200))).toBe("b".repeat(200));
  });

  it("muestra — para los vacíos", () => {
    expect(valorLegible(null)).toBe("—");
    expect(valorLegible("")).toBe("—");
  });
});

describe("diasRestantes", () => {
  it("lee los días de una notificación de cierre", () => {
    expect(diasRestantes({ dias_restantes: 5, fecha_cierre: "2026-11-01" })).toBe(5);
    expect(diasRestantes(null)).toBeNull();
    expect(diasRestantes([])).toBeNull();
  });
});

describe("agruparSuscripciones", () => {
  it("separa fondos, instituciones y temáticas", () => {
    const base = { convocatoria_id: null, valor: null, titulo_convocatoria: null, creado: "2026-10-01" };
    const lista: Suscripcion[] = [
      { ...base, id: 1, tipo: "convocatoria", convocatoria_id: 7, titulo_convocatoria: "Fondo X" },
      { ...base, id: 2, tipo: "institucion", valor: "ANII" },
      { ...base, id: 3, tipo: "tematica", valor: "Salud" },
      { ...base, id: 4, tipo: "convocatoria", convocatoria_id: 8 },
    ];
    const grupos = agruparSuscripciones(lista);
    expect(grupos.fondos.map((s) => s.id)).toEqual([1, 4]);
    expect(grupos.instituciones.map((s) => s.id)).toEqual([2]);
    expect(grupos.tematicas.map((s) => s.id)).toEqual([3]);
  });

  it("con lista vacía devuelve grupos vacíos", () => {
    expect(agruparSuscripciones([])).toEqual({ fondos: [], instituciones: [], tematicas: [] });
  });
});

describe("validarDias", () => {
  it("acepta los extremos del rango", () => {
    expect(validarDias(1)).toBeNull();
    expect(validarDias(60)).toBeNull();
  });

  it("rechaza fuera de rango y NaN", () => {
    expect(validarDias(0)).not.toBeNull();
    expect(validarDias(61)).not.toBeNull();
    expect(validarDias(Number.NaN)).not.toBeNull();
    expect(validarDias(2.5)).not.toBeNull();
  });
});
