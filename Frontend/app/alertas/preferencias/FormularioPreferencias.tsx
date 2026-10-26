"use client";

import { useActionState, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DIAS_MAXIMO, DIAS_MINIMO, validarDias, type Preferencias } from "@/lib/alertas";
import { Aviso } from "@/app/perfil/campos";
import { guardarPreferencias } from "../actions";

const TIPOS = [
  { name: "alerta_apertura", label: "Apertura de convocatorias", ayuda: "Cuando abre un fondo que seguís." },
  { name: "alerta_cierre", label: "Próximo cierre", ayuda: "Antes de que cierre un fondo que seguís." },
  { name: "alerta_actualizacion", label: "Actualizaciones de fondos", ayuda: "Cuando cambian fechas, requisitos u otros datos." },
] as const;

export default function FormularioPreferencias({ preferencias }: { preferencias: Preferencias }) {
  const router = useRouter();
  const [estado, accion, guardando] = useActionState(guardarPreferencias, null);
  const [dias, setDias] = useState(String(preferencias.dias_anticipacion_cierre));
  const errorDias = validarDias(Number(dias));

  useEffect(() => {
    if (estado?.ok) {
      router.refresh();
    }
  }, [estado, router]);

  return (
    <form
      key={JSON.stringify(preferencias)}
      action={accion}
      className="flex flex-col gap-5 rounded-3xl border-2 border-ink bg-paper p-6 shadow-sm"
    >
      <fieldset className="flex flex-col gap-3">
        <legend className="font-display mb-2 text-xl text-ink">Qué alertas querés recibir</legend>
        {TIPOS.map((tipo) => (
          <label key={tipo.name} className="flex items-start gap-3 text-sm text-ink">
            <input
              type="checkbox"
              name={tipo.name}
              defaultChecked={preferencias[tipo.name]}
              className="mt-0.5 h-4 w-4 accent-pine"
            />
            <span>
              {tipo.label}
              <span className="block text-xs text-ink/50">{tipo.ayuda}</span>
            </span>
          </label>
        ))}
      </fieldset>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="dias_anticipacion_cierre" className="flex flex-wrap items-center gap-2 text-sm text-ink">
          Avisarme del cierre con
          <input
            id="dias_anticipacion_cierre"
            name="dias_anticipacion_cierre"
            type="number"
            inputMode="numeric"
            min={DIAS_MINIMO}
            max={DIAS_MAXIMO}
            step={1}
            required
            value={dias}
            onChange={(evento) => setDias(evento.target.value)}
            aria-invalid={errorDias ? true : undefined}
            aria-describedby={errorDias ? "dias_error" : undefined}
            className="h-11 w-24 rounded-xl border-2 border-ink bg-foam/70 px-3 text-sm text-ink outline-none transition focus:border-pine focus:bg-paper"
          />
          días de anticipación
        </label>
        {errorDias ? (
          <p id="dias_error" role="alert" className="text-xs text-clay">
            {errorDias}
          </p>
        ) : null}
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="flex items-start gap-3 text-sm text-ink">
          <input
            type="checkbox"
            role="switch"
            name="email_habilitado"
            defaultChecked={preferencias.email_habilitado}
            className="mt-0.5 h-4 w-4 accent-pine"
          />
          <span>
            Recibir también por correo electrónico
            <span className="block text-xs text-ink/50">
              {preferencias.email
                ? `Te escribimos a ${preferencias.email}.`
                : "No hay un correo válido asociado a tu cuenta, así que solo vas a ver las alertas acá."}
            </span>
          </span>
        </label>
      </div>

      {estado ? <Aviso ok={estado.ok} texto={estado.mensaje} /> : null}

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={guardando || Boolean(errorDias)}
          className="rounded-full bg-pine px-5 py-2 text-sm font-medium text-ink shadow-sm transition hover:bg-pine-hover disabled:cursor-not-allowed disabled:opacity-60"
        >
          {guardando ? "Guardando..." : "Guardar preferencias"}
        </button>
      </div>
    </form>
  );
}
