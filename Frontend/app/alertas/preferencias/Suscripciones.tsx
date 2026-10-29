"use client";

import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import Combobox from "@/app/components/Combobox";
import {
  agruparSuscripciones,
  cuerpoSuscripcion,
  detalleRespuesta,
  nombreSuscripcion,
  type Opciones,
  type Suscripcion,
} from "@/lib/alertas";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";

const BOTON_QUITAR =
  "presionable inline-flex min-h-8 shrink-0 items-center rounded-full border-2 border-ink px-3 text-xs text-ink hover:bg-paper disabled:cursor-wait disabled:opacity-60 pointer-coarse:min-h-11 pointer-coarse:px-4 pointer-coarse:text-sm";

const BOTON_AGREGAR =
  "presionable h-11 shrink-0 rounded-full bg-pine px-5 text-sm font-medium text-ink shadow-sm hover:bg-pine-hover disabled:cursor-not-allowed disabled:opacity-60";

export default function Suscripciones({
  iniciales,
  opciones,
}: {
  iniciales: Suscripcion[];
  opciones: Opciones;
}) {
  const [suscripciones, setSuscripciones] = useState(iniciales);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const grupos = agruparSuscripciones(suscripciones);

  // Muestra el error en pantalla y también como aviso
  function fallo(mensaje: string) {
    setError(mensaje);
    toast.error(mensaje);
  }

  async function crear(cuerpo: object): Promise<Suscripcion | null> {
    setOcupado(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/alertas/suscripciones`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cuerpo),
      });
      if (!response.ok) {
        fallo(await detalleRespuesta(response));
        return null;
      }
      const nueva = (await response.json()) as Suscripcion;
      // 200: ya la seguía; no se duplica
      setSuscripciones((lista) =>
        lista.some((suscripcion) => suscripcion.id === nueva.id) ? lista : [...lista, nueva],
      );
      return nueva;
    } catch {
      fallo("No se pudo conectar con la API.");
      return null;
    } finally {
      setOcupado(false);
    }
  }

  async function quitar(suscripcion: Suscripcion) {
    setOcupado(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/alertas/suscripciones/${suscripcion.id}`, { method: "DELETE" });
      // 404: ya no existía, igual se saca de la lista
      if (!response.ok && response.status !== 404) {
        fallo(await detalleRespuesta(response));
        return;
      }
      setSuscripciones((lista) => lista.filter((item) => item.id !== suscripcion.id));

      // Deshacer = volver a crearla con los mismos datos (es idempotente en la API)
      const cuerpo = cuerpoSuscripcion(suscripcion);
      toast.success(`Dejaste de seguir ${nombreSuscripcion(suscripcion)}.`, {
        action: cuerpo ? { label: "Deshacer", onClick: () => void crear(cuerpo) } : undefined,
      });
    } catch {
      fallo("No se pudo conectar con la API.");
    } finally {
      setOcupado(false);
    }
  }

  async function agregar(tipo: "institucion" | "tematica", valor: string) {
    const nueva = await crear({ tipo, valor });
    if (nueva) toast.success(`Ahora seguís ${nombreSuscripcion(nueva)}.`);
    return nueva !== null;
  }

  return (
    <section className="flex flex-col gap-5 rounded-3xl border-2 border-ink bg-paper p-6 shadow-sm">
      <div>
        <h2 className="font-display text-xl text-ink">Lo que seguís</h2>
        <p className="mt-1 text-sm text-ink/70">Te avisamos de los fondos, instituciones y áreas temáticas de esta lista.</p>
      </div>

      {error ? (
        <p role="alert" className="rounded-2xl border border-clay/30 bg-clay/10 px-4 py-3 text-sm text-ink">
          {error}
        </p>
      ) : null}

      <Grupo titulo="Fondos">
        {grupos.fondos.length === 0 ? (
          <p className="text-sm text-ink/70">
            Todavía no seguís ningún fondo. Los fondos se siguen desde el{" "}
            <Link href="/repositorio" className="text-pine-text underline underline-offset-2">
              Repositorio
            </Link>
            .
          </p>
        ) : (
          <Lista>
            {grupos.fondos.map((suscripcion) => (
              <Item key={suscripcion.id} ocupado={ocupado} onQuitar={() => quitar(suscripcion)}>
                {suscripcion.convocatoria_id !== null ? (
                  <Link
                    href={`/repositorio/convocatorias/${suscripcion.convocatoria_id}`}
                    className="text-ink underline-offset-2 hover:underline"
                  >
                    {suscripcion.titulo_convocatoria ?? `Convocatoria #${suscripcion.convocatoria_id}`}
                  </Link>
                ) : (
                  <span>{suscripcion.titulo_convocatoria ?? `Suscripción #${suscripcion.id}`}</span>
                )}
              </Item>
            ))}
          </Lista>
        )}
      </Grupo>

      <Grupo titulo="Instituciones">
        <ListaValores lista={grupos.instituciones} vacio="No seguís ninguna institución." ocupado={ocupado} onQuitar={quitar} />
        <Agregar
          id="agregar_institucion"
          etiqueta="Institución a seguir"
          placeholder="Escribí o elegí una institución"
          opciones={opciones.instituciones}
          ocupado={ocupado}
          onAgregar={(valor) => agregar("institucion", valor)}
        />
      </Grupo>

      <Grupo titulo="Áreas temáticas">
        <ListaValores lista={grupos.tematicas} vacio="No seguís ninguna área temática." ocupado={ocupado} onQuitar={quitar} />
        <Agregar
          id="agregar_tematica"
          etiqueta="Área temática a seguir"
          placeholder="Escribí o elegí un área temática"
          opciones={opciones.tematicas}
          ocupado={ocupado}
          onAgregar={(valor) => agregar("tematica", valor)}
        />
      </Grupo>
    </section>
  );
}

function Grupo({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-3 border-t border-pine/10 pt-4">
      <h3 className="text-sm font-medium tracking-[0.12em] text-ink/70 uppercase">{titulo}</h3>
      {children}
    </div>
  );
}

function Lista({ children }: { children: React.ReactNode }) {
  return <ul className="flex flex-col gap-2">{children}</ul>;
}

function Item({
  ocupado,
  onQuitar,
  children,
}: {
  ocupado: boolean;
  onQuitar: () => void;
  children: React.ReactNode;
}) {
  return (
    <li className="flex items-center justify-between gap-3 rounded-2xl bg-foam/60 px-4 py-2 text-sm text-ink">
      <span className="min-w-0 break-words">{children}</span>
      <button type="button" disabled={ocupado} onClick={onQuitar} className={BOTON_QUITAR}>
        Quitar
      </button>
    </li>
  );
}

function ListaValores({
  lista,
  vacio,
  ocupado,
  onQuitar,
}: {
  lista: Suscripcion[];
  vacio: string;
  ocupado: boolean;
  onQuitar: (suscripcion: Suscripcion) => void;
}) {
  if (lista.length === 0) {
    return <p className="text-sm text-ink/70">{vacio}</p>;
  }
  return (
    <Lista>
      {lista.map((suscripcion) => (
        <Item key={suscripcion.id} ocupado={ocupado} onQuitar={() => onQuitar(suscripcion)}>
          <span>{suscripcion.valor}</span>
        </Item>
      ))}
    </Lista>
  );
}

function Agregar({
  id,
  etiqueta,
  placeholder,
  opciones,
  ocupado,
  onAgregar,
}: {
  id: string;
  etiqueta: string;
  placeholder: string;
  opciones: string[];
  ocupado: boolean;
  onAgregar: (valor: string) => Promise<boolean>;
}) {
  const [valor, setValor] = useState("");

  return (
    <form
      className="flex flex-col gap-2 sm:flex-row sm:items-center"
      onSubmit={async (evento) => {
        evento.preventDefault();
        if (valor && (await onAgregar(valor))) setValor("");
      }}
    >
      <Combobox
        id={id}
        options={opciones}
        value={valor}
        onChange={setValor}
        placeholder={placeholder}
        ariaLabel={etiqueta}
        disabled={ocupado}
      />
      <button type="submit" disabled={ocupado || !valor} className={BOTON_AGREGAR}>
        Agregar
      </button>
    </form>
  );
}
