"use client";

import { useActionState, useState } from "react";
import { cambiarContrasena } from "../actions";
import { Aviso, Campo, ESTILO_INPUT } from "../campos";

// Mismas reglas que la passwordPolicy del realm (la API y Keycloak las vuelven a validar)
const REGLAS = [
  { texto: "Al menos 12 caracteres", cumple: (valor: string) => valor.length >= 12 },
  { texto: "Al menos un número", cumple: (valor: string) => /\p{Nd}/u.test(valor) },
  { texto: "Al menos una mayúscula", cumple: (valor: string) => /\p{Lu}/u.test(valor) },
  { texto: "Al menos un carácter especial", cumple: (valor: string) => /[^\p{L}\p{N}]/u.test(valor) },
];

export default function FormularioContrasena() {
  const [estado, accion, guardando] = useActionState(cambiarContrasena, null);
  const [nueva, setNueva] = useState("");
  const [confirmacion, setConfirmacion] = useState("");
  const [visible, setVisible] = useState(false);

  const tipo = visible ? "text" : "password";
  const valida = REGLAS.every((regla) => regla.cumple(nueva)) && nueva === confirmacion;

  return (
    <form
      action={accion}
      className="flex flex-col gap-5 rounded-3xl border border-pine/10 bg-paper p-6 shadow-sm"
    >
      <Campo id="actual" label="Contraseña actual" requerido>
        <input id="actual" name="actual" type={tipo} required autoComplete="current-password" className={ESTILO_INPUT} />
      </Campo>

      <Campo id="nueva" label="Contraseña nueva" requerido>
        <input
          id="nueva"
          name="nueva"
          type={tipo}
          required
          autoComplete="new-password"
          value={nueva}
          onChange={(evento) => setNueva(evento.target.value)}
          className={ESTILO_INPUT}
        />
      </Campo>

      <ul className="grid gap-1 text-xs sm:grid-cols-2" aria-label="Requisitos de la contraseña">
        {REGLAS.map((regla) => {
          const cumple = regla.cumple(nueva);
          return (
            <li key={regla.texto} className={cumple ? "text-pine-text" : "text-ink/50"}>
              {cumple ? "✓" : "○"} {regla.texto}
            </li>
          );
        })}
      </ul>

      <Campo id="confirmacion" label="Repetí la contraseña nueva" requerido>
        <input
          id="confirmacion"
          name="confirmacion"
          type={tipo}
          required
          autoComplete="new-password"
          value={confirmacion}
          onChange={(evento) => setConfirmacion(evento.target.value)}
          aria-invalid={confirmacion !== "" && confirmacion !== nueva}
          className={ESTILO_INPUT}
        />
      </Campo>
      {confirmacion !== "" && confirmacion !== nueva ? (
        <p className="-mt-3 text-xs text-clay">Las contraseñas no coinciden.</p>
      ) : null}

      <label className="flex items-center gap-2 text-sm text-ink">
        <input type="checkbox" checked={visible} onChange={(evento) => setVisible(evento.target.checked)} />
        Mostrar contraseñas
      </label>

      {estado ? <Aviso ok={estado.ok} texto={estado.mensaje} /> : null}

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={guardando || !valida}
          className="rounded-full bg-pine px-5 py-2 text-sm font-medium text-ink shadow-sm transition hover:bg-pine-hover disabled:cursor-not-allowed disabled:opacity-60"
        >
          {guardando ? "Cambiando..." : "Cambiar contraseña"}
        </button>
      </div>
    </form>
  );
}
