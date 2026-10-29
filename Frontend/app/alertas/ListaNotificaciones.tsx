"use client";

import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import {
  LIMITE_NOTIFICACIONES,
  detalleRespuesta,
  diasRestantes,
  etiquetaTipo,
  fechaLegible,
  filasCambios,
  type Notificacion,
  type PaginaNotificaciones,
} from "@/lib/alertas";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";
const BASE = `${API_URL}/api/alertas/notificaciones`;

const LECTURA = [
  { valor: false, label: "Todas" },
  { valor: true, label: "No leídas" },
];

const TIPOS = [
  { valor: "", label: "Todos los tipos" },
  { valor: "apertura", label: "Apertura" },
  { valor: "cierre", label: "Próximo cierre" },
  { valor: "actualizacion", label: "Actualización" },
];

// Mismo peso de letra activa e inactiva: elegir un filtro no mueve el resto de la fila.
// En pantallas táctiles todos los botones llegan a 44px de alto.
const PILDORA_ACTIVA =
  "presionable inline-flex min-h-10 items-center rounded-full border border-pine bg-pine px-4 text-sm text-ink disabled:opacity-60 pointer-coarse:min-h-11";
const PILDORA =
  "presionable inline-flex min-h-10 items-center rounded-full border border-pine/30 bg-paper px-4 text-sm text-ink hover:border-pine hover:bg-foam disabled:cursor-wait disabled:opacity-60 pointer-coarse:min-h-11";
const BOTON =
  "presionable inline-flex min-h-10 items-center rounded-full border-2 border-ink px-4 text-sm text-ink hover:bg-foam disabled:cursor-wait disabled:opacity-60 pointer-coarse:min-h-11";
const BOTON_CHICO =
  "presionable inline-flex min-h-8 items-center rounded-full border-2 border-ink px-3 text-xs text-ink hover:bg-foam disabled:cursor-wait disabled:opacity-60 pointer-coarse:min-h-11 pointer-coarse:px-4 pointer-coarse:text-sm";

type Filtros = { soloNoLeidas: boolean; tipo: string; page: number };

export default function ListaNotificaciones({ inicial }: { inicial: PaginaNotificaciones }) {
  const [pagina, setPagina] = useState(inicial);
  const [filtros, setFiltros] = useState<Filtros>({ soloNoLeidas: false, tipo: "", page: 1 });
  const [abiertas, setAbiertas] = useState<Set<number>>(new Set());
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Ejecuta una llamada a la API con los botones deshabilitados y el error visible.
  // Si sale bien muestra el aviso de éxito (si hay); el error queda en pantalla y también como aviso.
  async function llamar(accion: () => Promise<void>, exito?: () => void) {
    setOcupado(true);
    setError(null);
    try {
      await accion();
      exito?.();
    } catch (excepcion) {
      const mensaje = excepcion instanceof Error ? excepcion.message : "No se pudo conectar con la API.";
      setError(mensaje);
      toast.error(mensaje);
    } finally {
      setOcupado(false);
    }
  }

  async function pedir(input: string, init?: RequestInit) {
    let response: Response;
    try {
      response = await fetch(input, init);
    } catch {
      throw new Error("No se pudo conectar con la API.");
    }
    if (!response.ok) throw new Error(await detalleRespuesta(response));
    return response;
  }

  async function traer(nuevos: Filtros) {
    const params = new URLSearchParams({
      solo_no_leidas: String(nuevos.soloNoLeidas),
      page: String(nuevos.page),
      limit: String(LIMITE_NOTIFICACIONES),
    });
    if (nuevos.tipo) params.set("tipo", nuevos.tipo);
    const datos = (await (await pedir(`${BASE}?${params}`)).json()) as PaginaNotificaciones;

    // Si se borró lo último de una página, se vuelve a la anterior
    if (datos.items.length === 0 && nuevos.page > 1 && datos.total > 0) {
      return traer({ ...nuevos, page: Math.max(1, datos.total_pages) });
    }
    setPagina(datos);
    setFiltros({ ...nuevos, page: datos.page || nuevos.page });
  }

  function cambiarFiltros(cambios: Partial<Filtros>) {
    setAbiertas(new Set());
    return llamar(() => traer({ ...filtros, page: 1, ...cambios }));
  }

  function reemplazar(actualizada: Notificacion, anterior: Notificacion) {
    setPagina((actual) => ({
      ...actual,
      items: actual.items.map((item) => (item.id === actualizada.id ? actualizada : item)),
      no_leidas: Math.max(0, actual.no_leidas + (anterior.leida ? 0 : -1) + (actualizada.leida ? 0 : 1)),
    }));
  }

  async function marcar(notificacion: Notificacion, leida: boolean) {
    const response = await pedir(`${BASE}/${notificacion.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ leida }),
    });
    const actualizada = (await response.json()) as Notificacion;
    reemplazar(actualizada, notificacion);
    return actualizada;
  }

  // Botón "Marcar como (no) leída": avisa y ofrece deshacer (vuelve al estado anterior con otro PATCH)
  function marcarConAviso(notificacion: Notificacion) {
    const leida = !notificacion.leida;
    let actualizada: Notificacion | null = null;
    llamar(
      async () => {
        actualizada = await marcar(notificacion, leida);
      },
      () =>
        toast.success(leida ? "Marcada como leída." : "Marcada como no leída.", {
          action: {
            label: "Deshacer",
            onClick: () => {
              const ultima = actualizada;
              if (ultima) llamar(async () => void (await marcar(ultima, !leida)));
            },
          },
        }),
    );
  }

  function alternar(notificacion: Notificacion) {
    const abierta = abiertas.has(notificacion.id);
    setAbiertas((actual) => {
      const nuevo = new Set(actual);
      if (abierta) nuevo.delete(notificacion.id);
      else nuevo.add(notificacion.id);
      return nuevo;
    });
    // Abrir una no leída la marca como leída
    if (!abierta && !notificacion.leida) {
      llamar(async () => void (await marcar(notificacion, true)));
    }
  }

  function eliminar(notificacion: Notificacion) {
    if (!window.confirm(`¿Eliminar la alerta "${notificacion.titulo}"?`)) return;
    // Sin "Deshacer": la API borra la alerta y no hay forma segura de recrearla igual
    llamar(
      async () => {
        await pedir(`${BASE}/${notificacion.id}`, { method: "DELETE" });
        await traer(filtros);
      },
      () => toast.success("Alerta eliminada."),
    );
  }

  function marcarTodas() {
    const cantidad = pagina.no_leidas;
    llamar(
      async () => {
        await pedir(`${BASE}/marcar-leidas`, { method: "POST" });
        await traer(filtros);
      },
      () => toast.success(cantidad === 1 ? "Marcaste 1 alerta como leída." : `Marcaste ${cantidad} alertas como leídas.`),
    );
  }

  function eliminarLeidas() {
    if (!window.confirm("¿Eliminar todas las alertas leídas? No se pueden recuperar.")) return;
    llamar(
      async () => {
        await pedir(`${BASE}?solo_leidas=true`, { method: "DELETE" });
        await traer({ ...filtros, page: 1 });
      },
      () => toast.success("Se eliminaron las alertas leídas."),
    );
  }

  const sinFiltros = !filtros.soloNoLeidas && !filtros.tipo;

  return (
    <section className="flex flex-col gap-4" aria-busy={ocupado}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por lectura">
          {LECTURA.map((opcion) => (
            <button
              key={opcion.label}
              type="button"
              disabled={ocupado}
              aria-pressed={filtros.soloNoLeidas === opcion.valor}
              onClick={() => cambiarFiltros({ soloNoLeidas: opcion.valor })}
              className={filtros.soloNoLeidas === opcion.valor ? PILDORA_ACTIVA : PILDORA}
            >
              {opcion.label}
            </button>
          ))}
          <span className="self-center text-sm text-ink/70" aria-live="polite">
            {pagina.no_leidas === 1 ? "1 sin leer" : `${pagina.no_leidas} sin leer`}
          </span>
        </div>

        <div className="flex flex-wrap gap-2">
          <button type="button" disabled={ocupado || pagina.no_leidas === 0} onClick={marcarTodas} className={BOTON}>
            Marcar todas como leídas
          </button>
          <button type="button" disabled={ocupado} onClick={eliminarLeidas} className={BOTON}>
            Eliminar leídas
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por tipo">
        {TIPOS.map((opcion) => (
          <button
            key={opcion.valor || "todos"}
            type="button"
            disabled={ocupado}
            aria-pressed={filtros.tipo === opcion.valor}
            onClick={() => cambiarFiltros({ tipo: opcion.valor })}
            className={filtros.tipo === opcion.valor ? PILDORA_ACTIVA : PILDORA}
          >
            {opcion.label}
          </button>
        ))}
      </div>

      {error ? (
        <p role="alert" className="rounded-2xl border border-clay/30 bg-clay/10 px-4 py-3 text-sm text-ink">
          {error}
        </p>
      ) : null}

      {pagina.items.length === 0 ? (
        <p className="rounded-3xl border-2 border-ink bg-paper p-6 text-sm text-ink/70">
          {sinFiltros ? (
            <>
              Todavía no tenés alertas. Seguí fondos desde el{" "}
              <Link href="/repositorio" className="text-pine-text underline underline-offset-2">
                Repositorio
              </Link>
              .
            </>
          ) : (
            "No hay alertas con estos filtros."
          )}
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {pagina.items.map((notificacion) => (
            <Item
              key={notificacion.id}
              notificacion={notificacion}
              abierta={abiertas.has(notificacion.id)}
              ocupado={ocupado}
              onAlternar={() => alternar(notificacion)}
              onMarcar={() => marcarConAviso(notificacion)}
              onEliminar={() => eliminar(notificacion)}
            />
          ))}
        </ul>
      )}

      {pagina.total_pages > 1 ? (
        <nav className="flex items-center justify-center gap-3" aria-label="Paginación de alertas">
          <button
            type="button"
            disabled={ocupado || filtros.page <= 1}
            onClick={() => llamar(() => traer({ ...filtros, page: filtros.page - 1 }))}
            className={BOTON}
          >
            Anterior
          </button>
          <span className="text-sm text-ink/70">
            Página {filtros.page} de {pagina.total_pages}
          </span>
          <button
            type="button"
            disabled={ocupado || filtros.page >= pagina.total_pages}
            onClick={() => llamar(() => traer({ ...filtros, page: filtros.page + 1 }))}
            className={BOTON}
          >
            Siguiente
          </button>
        </nav>
      ) : null}
    </section>
  );
}

function Item({
  notificacion,
  abierta,
  ocupado,
  onAlternar,
  onMarcar,
  onEliminar,
}: {
  notificacion: Notificacion;
  abierta: boolean;
  ocupado: boolean;
  onAlternar: () => void;
  onMarcar: () => void;
  onEliminar: () => void;
}) {
  // aria-controls solo apunta al panel cuando existe: cerrado no se renderiza
  const panelId = `alerta-${notificacion.id}`;
  const filas = notificacion.tipo === "actualizacion" ? filasCambios(notificacion.detalle) : [];
  const dias = notificacion.tipo === "cierre" ? diasRestantes(notificacion.detalle) : null;

  return (
    <li
      className={`rounded-3xl border-2 border-ink p-5 shadow-sm ${notificacion.leida ? "bg-paper" : "bg-foam"}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <button
          type="button"
          aria-expanded={abierta}
          aria-controls={abierta ? panelId : undefined}
          onClick={onAlternar}
          className="flex min-w-0 flex-1 flex-col items-start gap-1 rounded-xl text-left"
        >
          <span className="flex flex-wrap items-center gap-2 text-xs">
            {!notificacion.leida ? (
              <span className="flex items-center gap-1 font-medium text-clay">
                <span aria-hidden="true" className="h-2 w-2 rounded-full bg-clay" />
                No leída
              </span>
            ) : null}
            <span className="rounded-full border border-ink/40 bg-paper px-2.5 py-0.5 font-medium text-ink">
              {etiquetaTipo(notificacion.tipo)}
            </span>
            <time dateTime={notificacion.creado} className="text-ink/70">
              {fechaLegible(notificacion.creado)}
            </time>
            {notificacion.email_enviado_en ? (
              <span className="text-ink/70" title={fechaLegible(notificacion.email_enviado_en)}>
                · Enviada por correo
              </span>
            ) : null}
          </span>
          <span className={`text-base text-ink ${notificacion.leida ? "" : "font-semibold"}`}>
            {notificacion.titulo}
          </span>
        </button>

        <div className="flex shrink-0 gap-2">
          <button type="button" disabled={ocupado} onClick={onMarcar} className={BOTON_CHICO}>
            {notificacion.leida ? "Marcar como no leída" : "Marcar como leída"}
          </button>
          <button type="button" disabled={ocupado} onClick={onEliminar} className={BOTON_CHICO}>
            Eliminar
          </button>
        </div>
      </div>

      {abierta ? (
        <div id={panelId} className="entrada-panel mt-4 flex flex-col gap-3 border-t border-ink/10 pt-4 text-sm text-ink">
          {notificacion.mensaje ? <p className="whitespace-pre-line">{notificacion.mensaje}</p> : null}

          {dias !== null ? (
            <p className="font-medium">
              {dias <= 0 ? "Cierra hoy." : dias === 1 ? "Falta 1 día para el cierre." : `Faltan ${dias} días para el cierre.`}
            </p>
          ) : null}

          {filas.length > 0 ? (
            <div className="overflow-x-auto rounded-2xl border-2 border-ink">
              <table className="w-full min-w-[480px] text-left text-sm">
                <thead className="border-b border-pine/10 text-xs tracking-[0.12em] text-ink/70 uppercase">
                  <tr>
                    <th scope="col" className="px-4 py-2 font-medium">Campo</th>
                    <th scope="col" className="px-4 py-2 font-medium">Antes</th>
                    <th scope="col" className="px-4 py-2 font-medium">Después</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-pine/10">
                  {filas.map((fila, indice) => (
                    <tr key={`${fila.campo}-${indice}`}>
                      <th scope="row" className="px-4 py-2 font-medium">{fila.campo}</th>
                      <td className="px-4 py-2 text-ink/70">{fila.antes}</td>
                      <td className="px-4 py-2">{fila.despues}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          {notificacion.convocatoria_id !== null ? (
            <Link
              href={`/repositorio/convocatorias/${notificacion.convocatoria_id}`}
              className="presionable inline-flex min-h-10 items-center self-start rounded-full bg-pine px-4 text-sm font-medium text-ink shadow-sm hover:bg-pine-hover pointer-coarse:min-h-11"
            >
              Ver convocatoria
            </Link>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}
