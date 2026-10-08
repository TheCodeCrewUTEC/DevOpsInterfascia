"use client";

import { useMemo, useState } from "react";
import {
  agruparPorPagina,
  esObligatorio,
  etiquetaCampo,
  normalizarValor,
  type CampoFormulario,
} from "./formulario";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";

type Props = {
  jobId: number;
  campos: CampoFormulario[];
  onVolver: () => void;
};

type Estado = { tipo: "ok" | "error"; texto: string } | null;

function valoresIniciales(campos: CampoFormulario[]) {
  return Object.fromEntries(campos.map((campo) => [campo.id, normalizarValor(campo.respuesta)]));
}

export default function FormularioCompletado({ jobId, campos, onVolver }: Props) {
  const [valores, setValores] = useState<Record<number, string>>(() => valoresIniciales(campos));
  const [guardados, setGuardados] = useState<Record<number, string>>(() => valoresIniciales(campos));
  const [guardando, setGuardando] = useState(false);
  const [estado, setEstado] = useState<Estado>(null);

  const secciones = useMemo(() => agruparPorPagina(campos), [campos]);
  const pendientesDeGuardar = campos.filter((campo) => valores[campo.id] !== guardados[campo.id]);
  const completos = campos.filter((campo) => valores[campo.id]?.trim()).length;

  function cambiar(id: number, valor: string) {
    setValores((actuales) => ({ ...actuales, [id]: valor }));
    setEstado(null);
  }

  async function guardar(): Promise<boolean> {
    if (pendientesDeGuardar.length === 0) return true;

    setGuardando(true);
    setEstado(null);

    try {
      const response = await fetch(`${API_URL}/formularios/jobs/${jobId}/respuestas`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          pendientesDeGuardar.map((campo) => ({
            id: campo.id,
            respuesta: valores[campo.id].trim() || null,
          })),
        ),
      });

      if (!response.ok) {
        throw new Error(
          response.status === 401
            ? "Tu sesión venció. Volvé a iniciar sesión para guardar."
            : `No se pudieron guardar los cambios (${response.status}).`,
        );
      }

      setGuardados({ ...valores });
      setEstado({ tipo: "ok", texto: "Cambios guardados." });
      return true;
    } catch (err) {
      setEstado({
        tipo: "error",
        texto: err instanceof Error ? err.message : "No se pudieron guardar los cambios.",
      });
      return false;
    } finally {
      setGuardando(false);
    }
  }

  async function descargarPdf() {
    // El PDF se arma con lo guardado en la base: primero se guardan las correcciones
    if (await guardar()) {
      const enlace = document.createElement("a");
      enlace.href = `/consultor-ia/pdf/${jobId}`;
      enlace.download = `formulario-completado-${jobId}.pdf`;
      enlace.click();
    }
  }

  function volver() {
    if (
      pendientesDeGuardar.length > 0 &&
      !window.confirm("Tenés cambios sin guardar. ¿Querés salir igual?")
    ) {
      return;
    }
    onVolver();
  }

  if (campos.length === 0) {
    return (
      <div className="flex flex-col gap-4">
        <p className="rounded-3xl border border-pine/10 bg-paper p-6 text-sm text-ink/70">
          El consultor no encontró campos en el formulario.
        </p>
        <div className="flex justify-end">
          <BotonSecundario onClick={onVolver}>Volver</BotonSecundario>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="rounded-3xl border border-pine/10 bg-paper p-5 shadow-sm sm:p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <p className="text-sm text-ink">
            <span className="font-medium">{completos}</span> de {campos.length} campos completados
          </p>
          <p className="text-xs text-ink/60">
            Revisá cada campo: la IA puede equivocarse. Lo que corrijas queda guardado.
          </p>
        </div>
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-foam" aria-hidden="true">
          <div
            className="h-full rounded-full bg-pine transition-all"
            style={{ width: `${Math.round((completos / campos.length) * 100)}%` }}
          />
        </div>
      </div>

      {secciones.map((seccion) => (
        <section key={seccion.titulo} className="flex flex-col gap-4">
          <h2 className="text-xs font-medium tracking-[0.18em] text-clay uppercase">{seccion.titulo}</h2>

          <div className="flex flex-col gap-4 rounded-3xl border border-pine/10 bg-paper p-5 shadow-sm sm:p-6">
            {seccion.campos.map((campo) => (
              <Campo
                key={campo.id}
                campo={campo}
                valor={valores[campo.id] ?? ""}
                onChange={(valor) => cambiar(campo.id, valor)}
              />
            ))}
          </div>
        </section>
      ))}

      <div className="sticky bottom-4 z-10 flex flex-wrap items-center justify-between gap-3 rounded-full border border-pine/15 bg-paper/95 px-4 py-3 shadow-lg backdrop-blur sm:px-5">
        <p
          role={estado?.tipo === "error" ? "alert" : "status"}
          className={`text-sm ${estado?.tipo === "error" ? "text-clay" : "text-ink/70"}`}
        >
          {estado?.texto ??
            (pendientesDeGuardar.length > 0
              ? `${pendientesDeGuardar.length} cambio${pendientesDeGuardar.length === 1 ? "" : "s"} sin guardar`
              : "Todo guardado")}
        </p>
        <div className="flex flex-wrap gap-2">
          <BotonSecundario onClick={volver}>Volver</BotonSecundario>
          <BotonSecundario onClick={() => void guardar()} disabled={guardando || pendientesDeGuardar.length === 0}>
            {guardando ? "Guardando..." : "Guardar cambios"}
          </BotonSecundario>
          <button
            type="button"
            onClick={() => void descargarPdf()}
            disabled={guardando}
            className="rounded-full bg-pine px-5 py-2 text-sm font-medium text-ink shadow-sm transition hover:bg-pine-hover disabled:opacity-60"
          >
            Descargar PDF
          </button>
        </div>
      </div>
    </div>
  );
}

function Campo({
  campo,
  valor,
  onChange,
}: {
  campo: CampoFormulario;
  valor: string;
  onChange: (valor: string) => void;
}) {
  const id = `campo-${campo.id}`;
  const etiqueta = etiquetaCampo(campo.campo);
  const sinDatosIa = !campo.respuesta_ia?.trim();
  const sugerenciaIa = normalizarValor(campo.respuesta_ia);
  const editado = valor !== sugerenciaIa;
  const vacio = !valor.trim();

  const clases = `w-full rounded-xl border px-3 py-2.5 text-sm text-ink outline-none transition focus:border-pine focus:bg-paper ${
    vacio && esObligatorio(campo.campo) ? "border-gold bg-gold/10" : "border-pine/20 bg-foam/60"
  }`;

  let control;
  if (campo.tipo === "pregunta") {
    control = (
      <textarea id={id} rows={5} value={valor} onChange={(e) => onChange(e.target.value)} className={`${clases} resize-y leading-relaxed`} />
    );
  } else if (campo.tipo === "checkbox") {
    control = (
      <select id={id} value={valor} onChange={(e) => onChange(e.target.value)} className={clases}>
        <option value="">Sin indicar</option>
        <option value="Sí">Sí</option>
        <option value="No">No</option>
        {valor && valor !== "Sí" && valor !== "No" ? <option value={valor}>{valor}</option> : null}
      </select>
    );
  } else {
    control = (
      <input
        id={id}
        type={campo.tipo === "email" ? "email" : "text"}
        inputMode={campo.tipo === "numero" ? "numeric" : undefined}
        value={valor}
        onChange={(e) => onChange(e.target.value)}
        className={clases}
      />
    );
  }

  return (
    <div className="flex flex-col gap-2 border-b border-pine/10 pb-4 last:border-0 last:pb-0">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label htmlFor={id} className="text-sm font-medium text-ink">
          {etiqueta}
          {esObligatorio(campo.campo) ? <span className="text-clay"> *</span> : null}
        </label>
        {editado ? (
          <span className="flex items-center gap-2">
            <span className="rounded-full bg-foam px-2 py-0.5 text-xs text-pine-text">Editado</span>
            {campo.respuesta_ia ? (
              <button
                type="button"
                onClick={() => onChange(sugerenciaIa)}
                className="text-xs text-ink/60 underline-offset-2 hover:text-pine-text hover:underline"
              >
                Restaurar sugerencia de la IA
              </button>
            ) : null}
          </span>
        ) : null}
      </div>

      {control}

      {sinDatosIa && !editado ? (
        <p className="text-xs text-ink/60">La IA no encontró este dato en los documentos. Completalo a mano.</p>
      ) : null}

      {campo.fuentes.length > 0 ? (
        <p className="text-xs text-pine-text">
          Fuente:{" "}
          {campo.fuentes
            .map((fuente) => `${fuente.archivo}${fuente.pagina != null ? ` · pág. ${fuente.pagina}` : ""}`)
            .join(", ")}
        </p>
      ) : null}
    </div>
  );
}

function BotonSecundario({
  children,
  onClick,
  disabled,
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="rounded-full border border-pine/40 bg-paper px-4 py-2 text-sm text-ink transition hover:border-pine hover:bg-foam disabled:opacity-50"
    >
      {children}
    </button>
  );
}
