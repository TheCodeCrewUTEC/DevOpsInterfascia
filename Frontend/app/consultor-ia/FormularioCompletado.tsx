"use client";

import { useMemo, useState } from "react";
import Combobox from "../components/Combobox";
import {
  agruparPorPagina,
  esObligatorio,
  etiquetaCampo,
  filasDeTabla,
  normalizarValor,
  type CampoFormulario,
  type ColumnaTabla,
  type FilaTabla,
} from "./formulario";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";

type Props = {
  jobId: number;
  campos: CampoFormulario[];
  validado?: boolean;
  onVolver: () => void;
};

type Estado = { tipo: "ok" | "error"; texto: string } | null;

function valoresIniciales(campos: CampoFormulario[]) {
  return Object.fromEntries(campos.map((campo) => [campo.id, normalizarValor(campo.respuesta)]));
}

export default function FormularioCompletado({ jobId, campos, validado = false, onVolver }: Props) {
  const [valores, setValores] = useState<Record<number, string>>(() => valoresIniciales(campos));
  const [guardados, setGuardados] = useState<Record<number, string>>(() => valoresIniciales(campos));
  const [guardando, setGuardando] = useState(false);
  const [estado, setEstado] = useState<Estado>(null);
  const [confirmado, setConfirmado] = useState(validado);

  const secciones = useMemo(() => agruparPorPagina(campos), [campos]);
  const pendientesDeGuardar = campos.filter((campo) => valores[campo.id] !== guardados[campo.id]);
  const completos = campos.filter((campo) => celdaCompleta(campo, valores[campo.id] ?? "")).length;

  function cambiar(id: number, valor: string) {
    setValores((actuales) => {
      const siguientes = { ...actuales, [id]: valor };
      const campo = campos.find((item) => item.id === id);
      if (!campo?.selector) return siguientes;
      for (const hijo of campos) {
        if (hijo.depende_de !== campo.selector) continue;
        const lista = hijo.opciones_por_valor?.[valor] ?? [];
        if (siguientes[hijo.id] && !lista.includes(siguientes[hijo.id])) {
          siguientes[hijo.id] = "";
        }
      }
      return siguientes;
    });
    setEstado(null);
    setConfirmado(false);
  }

  // Human in the loop: la persona da por buenos los datos revisados y quedan
  // guardados para sugerirlos en el próximo formulario.
  async function confirmar() {
    if (!(await guardar())) return;

    setGuardando(true);
    try {
      const response = await fetch(`${API_URL}/formularios/jobs/${jobId}/confirmar`, { method: "POST" });
      if (!response.ok) {
        throw new Error(
          response.status === 401
            ? "Iniciá sesión para guardar los datos confirmados."
            : `No se pudieron confirmar los datos (${response.status}).`,
        );
      }
      const { guardados } = (await response.json()) as { guardados: number };
      setConfirmado(true);
      setEstado({
        tipo: "ok",
        texto: `Datos confirmados: ${guardados} campo${guardados === 1 ? "" : "s"} se sugerirán en tu próximo formulario.`,
      });
    } catch (err) {
      setEstado({
        tipo: "error",
        texto: err instanceof Error ? err.message : "No se pudieron confirmar los datos.",
      });
    } finally {
      setGuardando(false);
    }
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
      <div className="rounded-3xl border-2 border-ink bg-paper p-5 shadow-sm sm:p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <p className="text-sm text-ink">
            <span className="font-medium">{completos}</span> de {campos.length} campos completados
          </p>
          <p className="text-xs text-ink/60">
            Revisá cada campo: la IA puede equivocarse. Al confirmar, los datos quedan guardados para tus próximos formularios.
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

          <div className="flex flex-col gap-4 rounded-3xl border-2 border-ink bg-paper p-5 shadow-sm sm:p-6">
            {seccion.campos.map((campo) => {
              const mapa = campo.opciones_por_valor ?? {};
              const dependiente = Boolean(campo.depende_de && Object.keys(mapa).length > 0);
              const padre = dependiente
                ? campos.find((item) => item.selector === campo.depende_de)
                : undefined;
              const valorPadre = padre ? (valores[padre.id] ?? "") : "";
              const opciones = dependiente ? (mapa[valorPadre] ?? []) : (campo.opciones ?? []);
              const nombrePadre = etiquetaCampo(padre?.campo ?? "el campo anterior");

              return (
                <Campo
                  key={campo.id}
                  campo={campo}
                  valor={valores[campo.id] ?? ""}
                  onChange={(valor) => cambiar(campo.id, valor)}
                  opciones={opciones}
                  bloqueado={dependiente && !valorPadre}
                  aviso={
                    dependiente
                      ? valorPadre
                        ? `Opciones según ${nombrePadre}.`
                        : `Las opciones aparecen al elegir ${nombrePadre}.`
                      : undefined
                  }
                />
              );
            })}
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
          <BotonSecundario onClick={() => void confirmar()} disabled={guardando || confirmado}>
            {confirmado ? "Datos confirmados ✓" : "Confirmar datos"}
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

function celdaCompleta(campo: CampoFormulario, valor: string) {
  if (campo.tipo !== "tabla") return Boolean(valor.trim());
  return filasDeTabla(valor).some((fila) => Object.values(fila).some((celda) => celda.trim()));
}

function opcionesDeColumna(columna: ColumnaTabla, fila: FilaTabla, columnas: ColumnaTabla[]) {
  if (columna.depende_de) {
    const padre = columnas.find((candidata) => candidata.selector === columna.depende_de);
    const valorPadre = padre ? (fila[padre.etiqueta] ?? "") : "";
    return {
      opciones: columna.opciones_por_valor?.[valorPadre] ?? [],
      bloqueado: !valorPadre,
    };
  }
  return { opciones: columna.opciones ?? [], bloqueado: false };
}

function TablaFilas({
  columnas,
  valor,
  onChange,
}: {
  columnas: ColumnaTabla[];
  valor: string;
  onChange: (valor: string) => void;
}) {
  const filas = filasDeTabla(valor);

  function publicar(siguientes: FilaTabla[]) {
    onChange(siguientes.length > 0 ? JSON.stringify(siguientes) : "");
  }

  function cambiarCelda(indice: number, etiqueta: string, celda: string) {
    const selector = columnas.find((columna) => columna.etiqueta === etiqueta)?.selector;
    const siguientes = filas.map((fila, actual) => {
      if (actual !== indice) return fila;
      const actualizada = { ...fila, [etiqueta]: celda };
      if (!selector) return actualizada;
      for (const columna of columnas) {
        if (columna.depende_de !== selector) continue;
        const opciones = columna.opciones_por_valor?.[celda] ?? [];
        if (actualizada[columna.etiqueta] && !opciones.includes(actualizada[columna.etiqueta])) {
          actualizada[columna.etiqueta] = "";
        }
      }
      return actualizada;
    });
    publicar(siguientes);
  }

  function agregar() {
    const vacia: FilaTabla = {};
    for (const columna of columnas) vacia[columna.etiqueta] = "";
    publicar([...filas, vacia]);
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[36rem] border-collapse">
          <thead>
            <tr>
              {columnas.map((columna) => (
                <th key={columna.selector} className="px-1 pb-2 text-left text-xs font-medium text-ink/70">
                  {etiquetaCampo(columna.etiqueta)}
                  {columna.requerido ? <span className="text-clay"> *</span> : null}
                </th>
              ))}
              <th className="w-16" />
            </tr>
          </thead>
          <tbody>
            {filas.map((fila, indice) => (
              <tr key={indice}>
                {columnas.map((columna) => {
                  const celda = fila[columna.etiqueta] ?? "";
                  const { opciones, bloqueado } = opcionesDeColumna(columna, fila, columnas);
                  const esLista = columna.tipo === "select" || opciones.length > 0 || Boolean(columna.depende_de);
                  return (
                    <td key={columna.selector} className="px-1 py-1 align-top">
                      {esLista ? (
                        <Combobox
                          id={`tabla-${indice}-${columna.selector}`}
                          value={celda}
                          onChange={(nuevo) => cambiarCelda(indice, columna.etiqueta, nuevo)}
                          options={opciones}
                          disabled={bloqueado}
                          opcionVacia={bloqueado ? "Elegí el campo anterior" : "Sin indicar"}
                        />
                      ) : (
                        <input
                          value={celda}
                          onChange={(event) => cambiarCelda(indice, columna.etiqueta, event.target.value)}
                          type={columna.tipo === "email" ? "email" : "text"}
                          className="w-full min-w-36 rounded-xl border-2 border-ink bg-foam/60 px-3 py-2 text-sm text-ink outline-none focus:border-pine focus:bg-paper"
                        />
                      )}
                    </td>
                  );
                })}
                <td className="px-1 py-1 align-top">
                  <button
                    type="button"
                    onClick={() => publicar(filas.filter((_, actual) => actual !== indice))}
                    className="rounded-full px-2 py-2 text-sm text-ink/50 transition hover:text-clay"
                  >
                    Quitar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {filas.length === 0 ? <p className="text-xs text-ink/60">No hay filas cargadas.</p> : null}
      <button
        type="button"
        onClick={agregar}
        className="self-start rounded-full border border-ink/20 px-4 py-1.5 text-sm text-ink transition hover:border-pine hover:text-pine-text"
      >
        Agregar fila
      </button>
    </div>
  );
}

function Campo({
  campo,
  valor,
  onChange,
  opciones,
  bloqueado = false,
  aviso,
}: {
  campo: CampoFormulario;
  valor: string;
  onChange: (valor: string) => void;
  opciones?: string[];
  bloqueado?: boolean;
  aviso?: string;
}) {
  const id = `campo-${campo.id}`;
  const etiqueta = etiquetaCampo(campo.campo);
  const sinDatosIa = campo.tipo === "tabla" ? filasDeTabla(campo.respuesta_ia).length === 0 : !campo.respuesta_ia?.trim();
  const sugerenciaIa = campo.tipo === "tabla" ? (campo.respuesta_ia ?? "") : normalizarValor(campo.respuesta_ia);
  const editado = valor !== sugerenciaIa;
  const vacio = !celdaCompleta(campo, valor);

  const clases = `w-full rounded-xl border-2 px-3 py-2.5 text-sm text-ink outline-none transition focus:border-pine focus:bg-paper ${
    vacio && esObligatorio(campo.campo) ? "border-gold bg-gold/10" : "border-ink bg-foam/60"
  }`;

  let control;
  if (campo.tipo === "tabla") {
    control = <TablaFilas columnas={campo.columnas ?? []} valor={valor} onChange={onChange} />;
  } else if (campo.tipo === "pregunta") {
    control = (
      <textarea id={id} rows={5} value={valor} onChange={(e) => onChange(e.target.value)} className={`${clases} resize-y leading-relaxed`} />
    );
  } else if ((opciones ?? campo.opciones ?? []).length > 0 || campo.depende_de) {
    const lista = opciones ?? campo.opciones ?? [];
    control = (
      <Combobox
        id={id}
        value={valor}
        onChange={onChange}
        opcionVacia={bloqueado ? "Elegí el campo anterior" : "Sin indicar"}
        options={lista}
        disabled={bloqueado}
        invalid={vacio && esObligatorio(campo.campo)}
      />
    );
  } else if (campo.tipo === "checkbox") {
    control = (
      <Combobox
        id={id}
        value={valor}
        onChange={onChange}
        opcionVacia="Sin indicar"
        options={["Sí", "No", ...(valor && valor !== "Sí" && valor !== "No" ? [valor] : [])]}
      />
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
    <div className="flex flex-col gap-2 border-b border-ink/15 pb-4 last:border-0 last:pb-0">
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

      {aviso ? <p className="text-xs text-ink/60">{aviso}</p> : null}

      {campo.dato_guardado && valor.trim() !== campo.dato_guardado.trim() ? (
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-pine/30 bg-foam/60 px-3 py-2 text-xs text-ink/80">
          <span>
            Dato que confirmaste antes: <span className="font-medium text-ink">{campo.dato_guardado}</span>
          </span>
          <button
            type="button"
            onClick={() => onChange(campo.dato_guardado ?? "")}
            className="rounded-full bg-pine px-2.5 py-0.5 font-medium text-ink transition hover:bg-pine-hover"
          >
            Usar este dato
          </button>
        </div>
      ) : null}

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
