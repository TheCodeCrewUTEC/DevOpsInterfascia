import { describe, expect, it } from "vitest";
import { buscarSuscripcion, formatFecha, type Suscripcion } from "../lib/suscripciones";

const lista: Suscripcion[] = [
  { id: 1, tipo: "convocatoria", convocatoria_id: 10, valor: null, titulo_convocatoria: "Fondo A", creado: null },
  { id: 2, tipo: "institucion", convocatoria_id: null, valor: "ANII", titulo_convocatoria: null, creado: null },
  { id: 3, tipo: "tematica", convocatoria_id: null, valor: "Salud", titulo_convocatoria: null, creado: null },
];

describe("buscarSuscripcion", () => {
  it("encuentra la suscripción a una convocatoria por id", () => {
    expect(buscarSuscripcion(lista, "convocatoria", { convocatoriaId: 10 })?.id).toBe(1);
  });

  it("compara el valor sin distinguir mayúsculas ni espacios", () => {
    expect(buscarSuscripcion(lista, "institucion", { valor: "  anii " })?.id).toBe(2);
  });

  it("devuelve null si no hay coincidencia", () => {
    expect(buscarSuscripcion(lista, "convocatoria", { convocatoriaId: 99 })).toBeNull();
    expect(buscarSuscripcion(lista, "institucion", { valor: "Salud" })).toBeNull();
    expect(buscarSuscripcion(lista, "institucion", { valor: "" })).toBeNull();
    expect(buscarSuscripcion([], "tematica", { valor: "Salud" })).toBeNull();
  });
});

describe("formatFecha", () => {
  it("pasa una fecha ISO a dd/mm/aaaa", () => {
    expect(formatFecha("2026-03-15")).toBe("15/03/2026");
    expect(formatFecha("2026-03-15T10:30:00")).toBe("15/03/2026");
  });

  it("tolera valores vacíos o con otro formato", () => {
    expect(formatFecha(null)).toBe("Sin fecha");
    expect(formatFecha("")).toBe("Sin fecha");
    expect(formatFecha("mañana")).toBe("mañana");
  });
});
