// Tipos y helpers del formulario completado (pantalla editable y PDF).

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
  tipo: string | null;
  pagina: number | null;
  fuentes: Fuente[];
};

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

export function esObligatorio(campo: string) {
  return /\*\s*$/.test(campo);
}

// Los campos vienen en el orden del formulario; se agrupan por página del PDF original
export function agruparPorPagina(campos: CampoFormulario[]): SeccionFormulario[] {
  const secciones: SeccionFormulario[] = [];

  for (const campo of campos) {
    const titulo = campo.pagina != null ? `Página ${campo.pagina} del formulario` : "Campos del formulario";
    const ultima = secciones.at(-1);

    if (ultima && ultima.titulo === titulo) {
      ultima.campos.push(campo);
    } else {
      secciones.push({ titulo, campos: [campo] });
    }
  }

  return secciones;
}
