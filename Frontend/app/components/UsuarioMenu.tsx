"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

type UsuarioMenuProps = {
  nombre: string;
  admin: boolean;
};

// Nombre del usuario logueado; al hacer click despliega sus opciones
export default function UsuarioMenu({ nombre, admin }: UsuarioMenuProps) {
  const opciones = [
    { href: "/perfil", label: "Mi perfil" },
    { href: "/perfil/contrasena", label: "Cambiar contraseña" },
    ...(admin ? [{ href: "/admin/usuarios", label: "Gestión de usuarios" }] : []),
  ];
  const [abierto, setAbierto] = useState(false);
  const contenedor = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!abierto) return;

    function clickAfuera(evento: MouseEvent) {
      if (!contenedor.current?.contains(evento.target as Node)) setAbierto(false);
    }
    function tecla(evento: KeyboardEvent) {
      if (evento.key === "Escape") setAbierto(false);
    }

    document.addEventListener("mousedown", clickAfuera);
    document.addEventListener("keydown", tecla);
    return () => {
      document.removeEventListener("mousedown", clickAfuera);
      document.removeEventListener("keydown", tecla);
    };
  }, [abierto]);

  return (
    <div ref={contenedor} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={abierto}
        onClick={() => setAbierto((valor) => !valor)}
        title={nombre}
        className="flex max-w-48 items-center gap-1 rounded-full px-2 py-1 text-sm text-ink transition hover:bg-foam"
      >
        <span className="truncate">{nombre}</span>
        <svg
          width="12"
          height="12"
          viewBox="0 0 12 12"
          aria-hidden="true"
          className={`shrink-0 transition-transform ${abierto ? "rotate-180" : ""}`}
        >
          <path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
        </svg>
      </button>

      {abierto ? (
        <div
          role="menu"
          className="absolute right-0 z-50 mt-2 min-w-48 rounded-2xl border border-pine/10 bg-paper p-1.5 shadow-lg"
        >
          {opciones.map((opcion) => (
            <Link
              key={opcion.href}
              href={opcion.href}
              role="menuitem"
              onClick={() => setAbierto(false)}
              className="block rounded-xl px-3 py-2 text-sm whitespace-nowrap text-ink transition hover:bg-foam"
            >
              {opcion.label}
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  );
}
