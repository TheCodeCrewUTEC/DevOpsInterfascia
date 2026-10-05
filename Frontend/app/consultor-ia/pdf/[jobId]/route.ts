import { jsPDF } from "jspdf";
import { apiFetch } from "@/lib/api";
import {
  agruparPorPagina,
  esObligatorio,
  etiquetaCampo,
  normalizarValor,
  type CampoFormulario,
} from "../../formulario";

export const dynamic = "force-dynamic";

// Paleta del sitio (globals.css)
const TINTA: [number, number, number] = [16, 42, 60];
const TEXTO_SUAVE: [number, number, number] = [96, 116, 130];
const CELESTE: [number, number, number] = [0, 119, 163];
const BORDE: [number, number, number] = [204, 236, 249];

const MARGEN = 48;
const ANCHO_PAGINA = 595.28; // A4 en puntos
const ALTO_PAGINA = 841.89;
const ANCHO_TEXTO = ANCHO_PAGINA - MARGEN * 2;

// Las fuentes estándar del PDF solo tienen caracteres latinos (WinAnsi)
function limpiar(texto: string) {
  return texto
    .replace(/[‘’]/g, "'")
    .replace(/[“”]/g, '"')
    .replace(/[–—]/g, "-")
    .replace(/…/g, "...")
    .replace(/•/g, "-")
    .replace(/[^\x09\x0A\x0D\x20-\x7E\xA0-\xFF]/g, "");
}

export async function GET(
  _request: Request,
  context: { params: Promise<{ jobId: string }> },
) {
  const { jobId } = await context.params;

  if (!/^\d+$/.test(jobId)) {
    return new Response("Job inválido", { status: 400 });
  }

  const response = await apiFetch(`/formularios/jobs/${jobId}/resultado`, { cache: "no-store" });

  if (!response.ok) {
    return new Response("No se encontró el formulario", { status: response.status });
  }

  const resultado = (await response.json()) as { respuestas: CampoFormulario[] };
  const secciones = agruparPorPagina(resultado.respuestas ?? []);

  const doc = new jsPDF({ unit: "pt", format: "a4" });
  let y = MARGEN;

  function asegurarEspacio(alto: number) {
    if (y + alto > ALTO_PAGINA - MARGEN) {
      doc.addPage();
      y = MARGEN;
    }
  }

  // Encabezado
  doc.setFont("helvetica", "bold");
  doc.setFontSize(9);
  doc.setTextColor(...CELESTE);
  doc.text("INTERFASCIA · CONSULTOR IA", MARGEN, y);
  y += 22;

  doc.setFontSize(20);
  doc.setTextColor(...TINTA);
  doc.text("Formulario de postulación completado", MARGEN, y);
  y += 18;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.setTextColor(...TEXTO_SUAVE);
  const fecha = new Intl.DateTimeFormat("es-UY", {
    dateStyle: "long",
    timeZone: "America/Montevideo",
  }).format(new Date());
  doc.text(
    limpiar(`Generado el ${fecha} · Revisá los datos antes de enviarlos a la convocatoria.`),
    MARGEN,
    y,
  );
  y += 26;

  for (const seccion of secciones) {
    asegurarEspacio(60);

    doc.setDrawColor(...BORDE);
    doc.setLineWidth(1);
    doc.line(MARGEN, y, MARGEN + ANCHO_TEXTO, y);
    y += 18;

    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    doc.setTextColor(...CELESTE);
    doc.text(limpiar(seccion.titulo.toUpperCase()), MARGEN, y);
    y += 20;

    for (const campo of seccion.campos) {
      const etiqueta = limpiar(etiquetaCampo(campo.campo) + (esObligatorio(campo.campo) ? " *" : ""));
      const respuesta = normalizarValor(campo.respuesta).trim();
      const valor = respuesta ? limpiar(respuesta) : "";

      doc.setFont("helvetica", "bold");
      doc.setFontSize(9.5);
      const lineasEtiqueta = doc.splitTextToSize(etiqueta, ANCHO_TEXTO) as string[];

      doc.setFont("helvetica", "normal");
      doc.setFontSize(10.5);
      const lineasValor = doc.splitTextToSize(valor || "Sin completar", ANCHO_TEXTO - 16) as string[];

      const altoEtiqueta = lineasEtiqueta.length * 12;
      const altoCaja = lineasValor.length * 14 + 12;

      // Etiqueta y caja juntas en la misma página si entran; si no, la caja se parte
      asegurarEspacio(Math.min(altoEtiqueta + altoCaja + 14, ALTO_PAGINA - MARGEN * 2));

      doc.setFont("helvetica", "bold");
      doc.setFontSize(9.5);
      doc.setTextColor(...TINTA);
      doc.text(lineasEtiqueta, MARGEN, y);
      y += altoEtiqueta - 2;

      doc.setFont("helvetica", valor ? "normal" : "italic");
      doc.setFontSize(10.5);
      doc.setTextColor(...(valor ? TINTA : TEXTO_SUAVE));

      let restantes = lineasValor;
      while (restantes.length > 0) {
        const entran = Math.max(1, Math.floor((ALTO_PAGINA - MARGEN - y - 12) / 14));
        const tramo = restantes.slice(0, entran);
        const alto = tramo.length * 14 + 12;

        doc.setDrawColor(...BORDE);
        doc.setFillColor(244, 251, 254);
        doc.roundedRect(MARGEN, y, ANCHO_TEXTO, alto, 5, 5, "FD");
        doc.text(tramo, MARGEN + 8, y + 16);
        y += alto;

        restantes = restantes.slice(entran);
        if (restantes.length > 0) {
          doc.addPage();
          y = MARGEN;
        }
      }

      y += 14;
    }

    y += 6;
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

  return new Response(doc.output("arraybuffer"), {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": `attachment; filename="formulario-completado-${jobId}.pdf"`,
      "Cache-Control": "no-store",
    },
  });
}
