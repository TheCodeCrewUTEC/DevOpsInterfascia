// Misma fórmula que Backend/app/services/documento_uy.py.
// La pantalla la vuelve a correr al editar, para que el aviso siga al número.

import { filasDeTabla, type CampoFormulario, type ColumnaTabla, type FilaTabla } from "./formulario";

export type ClaseIdentificador = "rut" | "cedula" | "documento";

function plano(texto: string) {
  return texto
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .replace(/[*_]/g, " ")
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .join(" ");
}

function digitos(valor: string) {
  return (valor.match(/\d/g) ?? []).join("");
}

export function cedulaValida(valor: string) {
  const crudo = digitos(valor);
  if (crudo.length !== 7 && crudo.length !== 8) return false;
  const numero = crudo.padStart(8, "0");
  const factores = [2, 9, 8, 7, 6, 3, 4];
  const suma = factores.reduce((total, factor, indice) => total + Number(numero[indice]) * factor, 0);
  const verificador = (10 - (suma % 10)) % 10;
  return verificador === Number(numero[7]);
}

export function rutValido(valor: string) {
  const numero = digitos(valor);
  if (numero.length !== 12) return false;
  if (numero.slice(0, 2) < "01" || numero.slice(0, 2) > "22") return false;
  if (numero.slice(2, 8) === "000000" || numero.slice(8, 11) !== "001") return false;
  const factores = [4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const suma = factores.reduce((total, factor, indice) => total + Number(numero[indice]) * factor, 0);
  const resto = suma % 11;
  if (resto === 1) return false;
  const verificador = resto === 0 ? 0 : 11 - resto;
  return verificador === Number(numero[11]);
}

export function claseIdentificador(etiqueta: string): ClaseIdentificador | null {
  const nombre = plano(etiqueta);
  if (/(^| )rut( |$)/.test(nombre)) return "rut";
  if (nombre.includes("cedula")) return "cedula";
  if (
    nombre.includes("documento de identidad") ||
    nombre.includes("numero de documento") ||
    nombre.includes("nro de documento")
  ) {
    return "documento";
  }
  return null;
}

function esTipoDocumento(etiqueta: string) {
  return plano(etiqueta).startsWith("tipo de documento");
}

function esPaisDocumento(etiqueta: string) {
  return plano(etiqueta).includes("pais de documento");
}

function mensajeRut(valor: string) {
  if (!digitos(valor)) return null;
  return rutValido(valor) ? null : "el RUT no es válido.";
}

function mensajeCedula(valor: string) {
  if (!digitos(valor)) return null;
  return cedulaValida(valor) ? null : "la cédula no es válida.";
}

function aplicaCedula(tipo: string | null, pais: string | null) {
  if (tipo !== null && !plano(tipo).includes("cedula")) return false;
  if (pais !== null && pais.trim() && !plano(pais).includes("uruguay")) return false;
  return true;
}

function mensajeDeValor(clase: ClaseIdentificador, valor: string, tipo: string | null, pais: string | null) {
  if (clase === "rut") return mensajeRut(valor);
  if (clase === "cedula") {
    if (pais !== null && pais.trim() && !plano(pais).includes("uruguay")) return null;
    return mensajeCedula(valor);
  }
  if (clase === "documento" && aplicaCedula(tipo, pais)) return mensajeCedula(valor);
  return null;
}

function celda(fila: FilaTabla, columnas: { etiqueta: string }[], coincide: (etiqueta: string) => boolean) {
  const columna = columnas.find((candidata) => coincide(candidata.etiqueta));
  if (!columna) return null;
  return fila[columna.etiqueta] ?? "";
}

export function mensajeDeCelda(columna: ColumnaTabla, fila: FilaTabla, columnas: ColumnaTabla[]) {
  const clase = claseIdentificador(columna.etiqueta);
  if (!clase) return null;
  return mensajeDeValor(
    clase,
    fila[columna.etiqueta] ?? "",
    celda(fila, columnas, esTipoDocumento),
    celda(fila, columnas, esPaisDocumento),
  );
}

type CampoConValor = {
  campo: string;
  seccion?: string | null;
  tipo?: string | null;
  columnas?: ColumnaTabla[];
};

export function mensajesIdentificador(
  campo: CampoConValor,
  valor: string,
  campos: CampoConValor[],
  valorDe: (campo: CampoConValor) => string,
): string[] {
  const columnas = campo.columnas ?? [];
  if (campo.tipo === "tabla" || columnas.length > 0) {
    const titulo = campo.campo.replaceAll("*", "").trim();
    const avisos: string[] = [];
    filasDeTabla(valor).forEach((fila, indice) => {
      const tipo = celda(fila, columnas, esTipoDocumento);
      const pais = celda(fila, columnas, esPaisDocumento);
      for (const columna of columnas) {
        const clase = claseIdentificador(columna.etiqueta);
        if (!clase) continue;
        const mensaje = mensajeDeValor(clase, fila[columna.etiqueta] ?? "", tipo, pais);
        if (mensaje) {
          avisos.push(`${titulo}, fila ${indice + 1}, ${columna.etiqueta.replaceAll("*", "").trim()}: ${mensaje}`);
        }
      }
    });
    return avisos;
  }

  const clase = claseIdentificador(campo.campo);
  if (!clase) return [];
  const hermanos = campo.seccion
    ? campos.filter(
        (otro) =>
          otro !== campo &&
          otro.seccion === campo.seccion &&
          (otro.columnas?.length ?? 0) === 0 &&
          otro.tipo !== "tabla",
      )
    : [];
  const tipo = hermanos.find((otro) => esTipoDocumento(otro.campo));
  const pais = hermanos.find((otro) => esPaisDocumento(otro.campo));
  const mensaje = mensajeDeValor(
    clase,
    valor,
    tipo ? valorDe(tipo) : null,
    pais ? valorDe(pais) : null,
  );
  if (!mensaje) return [];
  return [`${campo.campo.replaceAll("*", "").trim()}: ${mensaje}`];
}

export function mensajesDelFormulario(campo: CampoFormulario, valor: string, campos: CampoFormulario[], valores: Record<number, string>) {
  return mensajesIdentificador(campo, valor, campos, (item) => valores[(item as CampoFormulario).id] ?? "");
}
