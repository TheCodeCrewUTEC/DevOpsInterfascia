"use client";

import Link from "next/link";
import { useState } from "react";
import Combobox from "@/app/components/Combobox";
import { agruparSuscripciones, detalleRespuesta, type Opciones, type Suscripcion } from "@/lib/alertas";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";

const BOTON_QUITAR =
  "rounded-full border-2 border-ink px-3 py-1 text-xs text-ink transition hover:bg-foam disabled:cursor-wait disabled:opacity-60";

const BOTON_AGREGAR =
  "h-11 shrink-0 rounded-full bg-pine px-5 text-sm font-medium text-ink shadow-sm transition hover:bg-pine-hover disabled:cursor-not-allowed disabled:opacity-60";

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

  async function quitar(id: number) {
    setOcupado(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/alertas/suscripciones/${id}`, { method: "DELETE" });
      // 404: ya no existía, igual se saca de la lista
      if (!response.ok && response.status !== 404) {
        setError(await detalleRespuesta(response));
        return;
      }
      setSuscripciones((lista) => lista.filter((suscripcion) => suscripcion.id !== id));
    } catch {
      setError("No se pudo conectar con la API.");
    } finally {
      setOcupado(false);
    }
  }

  async function agregar(tipo: "institucion" | "tematica", valor: string) {
    setOcupado(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/api/alertas/suscripciones`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tipo, valor }),
      });
      if (!response.ok) {
        setError(await detalleRespuesta(response));
        return false;
      }
      const nueva = (await response.json()) as Suscripcion;
      // 200: ya la seguía; no se duplica
      setSuscripciones((lista) =>
        lista.some((suscripcion) => suscripcion.id === nueva.id) ? lista : [...lista, nueva],
      );
      return true;
    } catch {
      setError("No se pudo conectar con la API.");
      return false;
    } finally {
      setOcupado(false);
    }
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
          <p className="text-sm text-ink/60">
            Todavía no seguís ningún fondo. Los fondos se siguen desde el{" "}
            <Link href="/repositorio" className="text-pine-text underline underline-offset-2">
              Repositorio
            </Link>
            .
          </p>
        ) : (
          <Lista>
            {grupos.fondos.map((suscripcion) => (
              <Item key={suscripcion.id} ocupado={ocupado} onQuitar={() => quitar(suscripcion.id)}>
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
      <h3 className="text-sm font-medium tracking-[0.12em] text-ink/60 uppercase">{titulo}</h3>
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
      {children}
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
  onQuitar: (id: number) => void;
}) {
  if (lista.length === 0) {
    return <p className="text-sm text-ink/60">{vacio}</p>;
  }
  return (
    <Lista>
      {lista.map((suscripcion) => (
        <Item key={suscripcion.id} ocupado={ocupado} onQuitar={() => onQuitar(suscripcion.id)}>
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
