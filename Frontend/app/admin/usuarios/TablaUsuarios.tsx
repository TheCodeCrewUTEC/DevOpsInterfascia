"use client";

import { useState, useTransition } from "react";
import { cambiarHabilitado, cambiarRol, type Resultado } from "./actions";

export type Usuario = {
  keycloak_id: string;
  email: string | null;
  nombre: string | null;
  apellido: string | null;
  perfil: string | null;
  perfil_otro: string | null;
  rol: string | null;
  estado: "pendiente" | "aprobado" | "rechazado";
};

const ROLES = [
  { valor: "", label: "Sin rol" },
  { valor: "admin", label: "Administrador" },
  { valor: "gestor_innovacion", label: "Gestor/a de innovación" },
  { valor: "investigador", label: "Investigador/a" },
  { valor: "emprendedor", label: "Emprendedor/a / Empresario/a" },
];

function nombreCompleto(usuario: Usuario) {
  const nombre = [usuario.nombre, usuario.apellido].filter(Boolean).join(" ");
  return nombre || usuario.email || "Sin nombre";
}

function perfilElegido(usuario: Usuario) {
  if (usuario.perfil === "Otros" && usuario.perfil_otro) {
    return `Otros: ${usuario.perfil_otro}`;
  }
  return usuario.perfil;
}

export default function TablaUsuarios({
  usuarios,
  miId,
}: {
  usuarios: Usuario[];
  miId: string | null;
}) {
  const [aviso, setAviso] = useState<Resultado | null>(null);

  return (
    <div className="flex flex-col gap-4">
      {aviso ? (
        <p
          role={aviso.ok ? "status" : "alert"}
          className={
            aviso.ok
              ? "rounded-2xl border border-pine/30 bg-foam px-4 py-3 text-sm text-ink"
              : "rounded-2xl border border-clay/30 bg-clay/10 px-4 py-3 text-sm text-ink"
          }
        >
          {aviso.mensaje}
        </p>
      ) : null}

      <div className="overflow-x-auto rounded-3xl border border-pine/10 bg-paper shadow-sm">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="border-b border-pine/10 text-xs tracking-[0.12em] text-ink/50 uppercase">
            <tr>
              <th scope="col" className="px-5 py-3 font-medium">Usuario</th>
              <th scope="col" className="px-5 py-3 font-medium">Estado</th>
              <th scope="col" className="px-5 py-3 font-medium">Rol</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-pine/10">
            {usuarios.map((usuario) => (
              <Fila
                key={usuario.keycloak_id}
                usuario={usuario}
                esYo={usuario.keycloak_id === miId}
                onResultado={setAviso}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Fila({
  usuario,
  esYo,
  onResultado,
}: {
  usuario: Usuario;
  esYo: boolean;
  onResultado: (resultado: Resultado) => void;
}) {
  const nombre = nombreCompleto(usuario);
  const perfil = perfilElegido(usuario);
  const [habilitado, setHabilitado] = useState(usuario.estado === "aprobado");
  const [rol, setRol] = useState(usuario.rol ?? "");
  const [guardando, startTransition] = useTransition();

  function alternar() {
    const nuevo = !habilitado;
    setHabilitado(nuevo);
    startTransition(async () => {
      const resultado = await cambiarHabilitado(usuario.keycloak_id, nombre, nuevo);
      if (!resultado.ok) setHabilitado(!nuevo);
      onResultado(resultado);
    });
  }

  function elegirRol(nuevo: string) {
    const anterior = rol;
    setRol(nuevo);
    startTransition(async () => {
      const resultado = await cambiarRol(usuario.keycloak_id, nombre, nuevo);
      if (!resultado.ok) setRol(anterior);
      onResultado(resultado);
    });
  }

  return (
    <tr className={guardando ? "opacity-60" : undefined}>
      <td className="px-5 py-4 align-middle">
        <p className="font-medium text-ink">
          {nombre}
          {esYo ? <span className="ml-2 text-xs font-normal text-ink/50">(vos)</span> : null}
        </p>
        <p className="break-all text-ink/70">{usuario.email}</p>
        {perfil ? <p className="mt-1 text-xs text-ink/50">Perfil: {perfil}</p> : null}
      </td>

      <td className="px-5 py-4 align-middle">
        <Interruptor
          activo={habilitado}
          deshabilitado={esYo || guardando}
          etiqueta={`Habilitar a ${nombre}`}
          onCambio={alternar}
        />
        {usuario.estado === "pendiente" && !habilitado ? (
          <p className="mt-1 text-xs text-ink/50">Pendiente de aprobación</p>
        ) : null}
      </td>

      <td className="px-5 py-4 align-middle">
        <select
          value={rol}
          disabled={esYo || guardando}
          aria-label={`Rol de ${nombre}`}
          onChange={(evento) => elegirRol(evento.target.value)}
          className="w-full max-w-60 rounded-xl border border-pine/30 bg-paper px-3 py-2 text-sm text-ink transition hover:border-pine focus:border-pine focus:outline-none focus:ring-2 focus:ring-pine/30 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {ROLES.map((opcion) => (
            <option key={opcion.valor} value={opcion.valor}>
              {opcion.label}
            </option>
          ))}
        </select>
      </td>
    </tr>
  );
}

// Interruptor tipo switch, como el de "Habilitado" en la consola de Keycloak
function Interruptor({
  activo,
  deshabilitado,
  etiqueta,
  onCambio,
}: {
  activo: boolean;
  deshabilitado: boolean;
  etiqueta: string;
  onCambio: () => void;
}) {
  return (
    <label
      className={`inline-flex items-center gap-3 ${deshabilitado ? "cursor-not-allowed opacity-60" : "cursor-pointer"}`}
    >
      <button
        type="button"
        role="switch"
        aria-checked={activo}
        aria-label={etiqueta}
        disabled={deshabilitado}
        onClick={onCambio}
        className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pine/50 focus-visible:ring-offset-2 disabled:cursor-not-allowed ${
          activo ? "bg-pine-text" : "bg-ink/25"
        }`}
      >
        <span
          aria-hidden="true"
          className={`inline-block h-5 w-5 rounded-full bg-white shadow transition-transform duration-200 ${
            activo ? "translate-x-[22px]" : "translate-x-0.5"
          }`}
        />
      </button>
      <span className="text-sm text-ink" aria-hidden="true">
        {activo ? "Habilitado" : "Deshabilitado"}
      </span>
    </label>
  );
}
