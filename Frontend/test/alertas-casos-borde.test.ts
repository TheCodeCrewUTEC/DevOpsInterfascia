import { describe, expect, it } from "vitest";
import { detalleRespuesta, diasRestantes, fechaLegible, filasCambios } from "../lib/alertas";
import { buscarSuscripcion, type Suscripcion } from "../lib/suscripciones";

describe("detalleRespuesta", () => {
  it("usa el detail de la API", async () => {
    const response = new Response(JSON.stringify({ detail: "No hay un correo válido" }), { status: 400 });
    expect(await detalleRespuesta(response)).toBe("No hay un correo válido");
  });

  it("con detail de validación (lista) o sin JSON muestra el código", async () => {
    const validacion = new Response(JSON.stringify({ detail: [{ msg: "x" }] }), { status: 422 });
    expect(await detalleRespuesta(validacion)).toBe("Error 422");
    expect(await detalleRespuesta(new Response("<html>", { status: 502 }))).toBe("Error 502");
    expect(await detalleRespuesta(new Response(null, { status: 401 }))).toBe("Error 401");
  });
});

describe("fechaLegible", () => {
  it("devuelve el texto original si no es una fecha", () => {
    expect(fechaLegible("no-es-fecha")).toBe("no-es-fecha");
  });
});

describe("filasCambios con valores no string", () => {
  it("muestra números y objetos sin romper", () => {
    expect(filasCambios([{ campo: "financiamiento", antes: 100, despues: { a: 1 } }])).toEqual([
      { campo: "Financiamiento", antes: "100", despues: '{"a":1}' },
    ]);
  });
});

describe("diasRestantes", () => {
  it("ignora listas y días no numéricos", () => {
    expect(diasRestantes([{ dias_restantes: 3 }])).toBeNull();
    expect(diasRestantes({ dias_restantes: "3" })).toBeNull();
    expect(diasRestantes({ dias_restantes: 0 })).toBe(0);
  });
});

describe("buscarSuscripcion casos borde", () => {
  const lista: Suscripcion[] = [
    { id: 1, tipo: "institucion", convocatoria_id: null, valor: "  ANII ", titulo_convocatoria: null, creado: null },
  ];

  it("valor vacío no coincide con nada", () => {
    expect(buscarSuscripcion(lista, "institucion", { valor: "   " })).toBeNull();
    expect(buscarSuscripcion(lista, "institucion", { valor: null })).toBeNull();
  });

  it("no mezcla tipos", () => {
    expect(buscarSuscripcion(lista, "tematica", { valor: "anii" })).toBeNull();
  });
});
