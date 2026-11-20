// Tipos y helpers del formulario completado (pantalla editable y PDF).

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";

export async function cancelarGeneracion(jobId: number, consultaToken?: string | null) {
  const consulta = consultaToken ? `?consulta=${encodeURIComponent(consultaToken)}` : "";
  const response = await fetch(`${API_URL}/formularios/jobs/${jobId}/cancelar${consulta}`, {
    method: "POST",
    credentials: "include",
  });

  if (response.status === 409) return;
  if (!response.ok) {
    throw new Error("No se pudo cancelar la generación.");
  }
}

export type Fuente = {
  pagina: number | null;
  archivo: string;
};

export type CampoFormulario = {
  id: number;
  campo: string;
  respuesta: string | null;
  respuesta_ia: string | null;
  editada: boolean;
  // Valor que la persona confirmó en un formulario anterior (human in the loop)
  dato_guardado: string | null;
  tipo: string | null;
  pagina: number | null;
  seccion?: string | null;
  detalle?: string | null;
  fuentes: Fuente[];
  opciones?: string[];
  selector?: string | null;
  depende_de?: string | null;
  opciones_por_valor?: Record<string, string[]>;
  columnas?: ColumnaTabla[];
};

export type ColumnaTabla = {
  etiqueta: string;
  tipo: string;
  requerido?: boolean;
  opciones: string[];
  selector: string;
  depende_de?: string | null;
  opciones_por_valor?: Record<string, string[]>;
};

export type FilaTabla = Record<string, string>;

export function columnasDe(valor: unknown): ColumnaTabla[] {
  if (!Array.isArray(valor)) return [];
  return valor.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const columna = item as Partial<ColumnaTabla>;
    if (typeof columna.etiqueta !== "string" || typeof columna.selector !== "string") return [];
    return [
      {
        etiqueta: columna.etiqueta,
        tipo: typeof columna.tipo === "string" ? columna.tipo : "text",
        requerido: Boolean(columna.requerido),
        opciones: listaDeOpciones(columna.opciones),
        selector: columna.selector,
        depende_de: typeof columna.depende_de === "string" ? columna.depende_de : null,
        opciones_por_valor: mapaDeOpciones(columna.opciones_por_valor),
      },
    ];
  });
}

export function filasDeTabla(valor: string | null | undefined): FilaTabla[] {
  if (!valor?.trim()) return [];
  try {
    const datos = JSON.parse(valor) as unknown;
    if (!Array.isArray(datos)) return [];
    return datos.flatMap((item) => {
      if (!item || typeof item !== "object" || Array.isArray(item)) return [];
      const fila: FilaTabla = {};
      for (const [clave, celda] of Object.entries(item)) {
        fila[clave] = celda == null ? "" : String(celda);
      }
      return [fila];
    });
  } catch {
    return [];
  }
}

export function textoDeTabla(valor: string | null | undefined, columnas: ColumnaTabla[]): string {
  const filas = filasDeTabla(valor);
  if (filas.length === 0) return "";
  return filas
    .map((fila, indice) => {
      const celdas = (columnas.length > 0 ? columnas : Object.keys(fila).map((etiqueta) => ({ etiqueta }))).map(
        (columna) => `${etiquetaCampo(columna.etiqueta)}: ${(fila[columna.etiqueta] || "").trim() || "—"}`,
      );
      return `${indice + 1}. ${celdas.join(" · ")}`;
    })
    .join("\n");
}

export function listaDeOpciones(valor: unknown): string[] {
  if (!Array.isArray(valor)) return [];
  return valor.filter((opcion): opcion is string => typeof opcion === "string" && opcion.trim() !== "");
}

export function mapaDeOpciones(valor: unknown): Record<string, string[]> {
  if (!valor || typeof valor !== "object" || Array.isArray(valor)) return {};
  const mapa: Record<string, string[]> = {};
  for (const [clave, lista] of Object.entries(valor)) {
    const opciones = listaDeOpciones(lista);
    if (clave.trim() && opciones.length > 0) mapa[clave] = opciones;
  }
  return mapa;
}

export type SeccionFormulario = {
  titulo: string;
  campos: CampoFormulario[];
};

// Quita el asterisco de obligatorio que trae la etiqueta del PDF ("RUT *" → "RUT")
export function etiquetaCampo(campo: string) {
  return campo.replace(/\s*\*+\s*$/, "").trim();
}

// La IA a veces responde casillas con true/false: se muestran como Sí/No
export function normalizarValor(valor: string | null | undefined) {
  const texto = (valor ?? "").trim();
  if (/^(true|s[ií]|yes)$/i.test(texto)) return "Sí";
  if (/^(false|no)$/i.test(texto)) return "No";
  return valor ?? "";
}

export function textosDetalle(detalle: string | null | undefined) {
  return (detalle ?? "")
    .split("\n")
    .map((linea) => linea.trim())
    .filter(Boolean);
}

export function esObligatorio(campo: string) {
  return /\*\s*$/.test(campo);
}

// Los campos vienen en el orden del formulario; se agrupan por página del PDF original
export function agruparPorPagina(campos: CampoFormulario[]): SeccionFormulario[] {
  const secciones: SeccionFormulario[] = [];

  for (const campo of campos) {
    const titulo = campo.seccion?.trim()
      ? campo.seccion
      : campo.pagina != null
        ? `Página ${campo.pagina} del formulario`
        : "Campos del formulario";
    const ultima = secciones.at(-1);

    if (ultima && ultima.titulo === titulo) {
      ultima.campos.push(campo);
    } else {
      secciones.push({ titulo, campos: [campo] });
    }
  }

  return secciones;
}
