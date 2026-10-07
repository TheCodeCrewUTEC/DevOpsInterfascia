"use client";

import { useActionState, useState } from "react";
import { cambiarContrasena } from "../actions";
import { Aviso, Campo, ESTILO_INPUT } from "../campos";

// Mismas reglas que la passwordPolicy del realm: length(12) y complejidad(3)
// (la API y Keycloak las vuelven a validar)
const CATEGORIAS_MINIMAS = 3;
const CATEGORIAS = [
  { texto: "Una mayúscula", cumple: (valor: string) => /\p{Lu}/u.test(valor) },
  { texto: "Una minúscula", cumple: (valor: string) => /\p{Ll}/u.test(valor) },
  { texto: "Un número", cumple: (valor: string) => /\p{Nd}/u.test(valor) },
  { texto: "Un carácter especial", cumple: (valor: string) => /[^\p{L}\p{N}]/u.test(valor) },
];
const REGLAS = [
  { texto: "Al menos 12 caracteres", cumple: (valor: string) => valor.length >= 12 },
  {
    texto: `Al menos ${CATEGORIAS_MINIMAS} de estas 4:`,
    cumple: (valor: string) => CATEGORIAS.filter((categoria) => categoria.cumple(valor)).length >= CATEGORIAS_MINIMAS,
  },
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

      <ul className="grid gap-1 text-xs" aria-label="Requisitos de la contraseña">
        {REGLAS.map((regla) => {
          const cumple = regla.cumple(nueva);
          return (
            <li key={regla.texto} className={cumple ? "text-pine-text" : "text-ink/50"}>
              {cumple ? "✓" : "○"} {regla.texto}
            </li>
          );
        })}
        <li>
          <ul className="grid gap-1 pl-4 sm:grid-cols-2">
            {CATEGORIAS.map((categoria) => {
              const cumple = categoria.cumple(nueva);
              return (
                <li key={categoria.texto} className={cumple ? "text-pine-text" : "text-ink/50"}>
                  {cumple ? "✓" : "○"} {categoria.texto}
                </li>
              );
            })}
          </ul>
        </li>
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
