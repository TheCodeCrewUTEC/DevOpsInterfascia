import { describe, expect, it } from "vitest";
import { cedulaValida, mensajesIdentificador, rutValido } from "../app/consultor-ia/identificacion";

describe("dígito verificador uruguayo", () => {
  it("valida la cédula con o sin puntos", () => {
    expect(cedulaValida("12345672")).toBe(true);
    expect(cedulaValida("1.234.567-2")).toBe(true);
    expect(cedulaValida("12345673")).toBe(false);
    expect(cedulaValida("1234567")).toBe(false);
  });

  it("valida el RUT de 12 dígitos", () => {
    expect(rutValido("211003420017")).toBe(true);
    expect(rutValido("21-100342-001-7")).toBe(true);
    expect(rutValido("211406340011")).toBe(true);
    expect(rutValido("210303670014")).toBe(false);
    expect(rutValido("123456789010")).toBe(false);
  });

  it("avisa según el nombre y el tipo de documento de la fila", () => {
    const rut = { campo: "RUT *", seccion: "Empresa", tipo: "text" };
    expect(mensajesIdentificador(rut, "210303670014", [rut], () => "")).toEqual(["RUT: el RUT no es válido."]);
    expect(mensajesIdentificador(rut, "21-100342-001-7", [rut], () => "")).toEqual([]);

    const tabla = {
      campo: "Titulares *",
      seccion: "Titulares",
      tipo: "tabla",
      columnas: [
        { etiqueta: "Tipo de documento *", tipo: "select", requerido: true, opciones: [], selector: "tipo" },
        { etiqueta: "Número de documento de identidad *", tipo: "text", requerido: true, opciones: [], selector: "nro" },
        { etiqueta: "País de documento *", tipo: "select", requerido: true, opciones: [], selector: "pais" },
      ],
    };
    const filas = JSON.stringify([
      {
        "Tipo de documento *": "Otro",
        "Número de documento de identidad *": "12345673",
        "País de documento *": "Uruguay (UY)",
      },
    ]);
    expect(mensajesIdentificador(tabla, filas, [tabla], () => "")).toEqual([]);
  });
});
