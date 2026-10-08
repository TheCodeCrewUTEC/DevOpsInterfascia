"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

const opciones = [
  { href: "/consultor-ia/relacionar", label: "Relacionar" },
  { href: "/consultor-ia/postular", label: "Postular" },
];

export default function ConsultorMenu() {
  const [abierto, setAbierto] = useState(false);
  const contenedor = useRef<HTMLDivElement>(null);
  const ruta = usePathname();
  const activo = ruta.startsWith("/consultor-ia");

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
        data-activo={activo ? "true" : undefined}
        onClick={() => setAbierto((valor) => !valor)}
        className="nav-link inline-flex items-center gap-1 text-xs text-ink/80 transition-colors hover:text-pine sm:text-sm md:whitespace-nowrap"
      >
        Consultor IA
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
          className="absolute left-1/2 z-50 mt-3 min-w-40 -translate-x-1/2 rounded-2xl border border-pine/10 bg-paper p-1.5 shadow-lg"
        >
          {opciones.map((opcion) => {
            const actual = ruta === opcion.href || ruta.startsWith(`${opcion.href}/`);
            return (
              <Link
                key={opcion.href}
                href={opcion.href}
                role="menuitem"
                aria-current={actual ? "page" : undefined}
                onClick={() => setAbierto(false)}
                className={`block rounded-xl px-3 py-2 text-sm whitespace-nowrap transition hover:bg-foam ${
                  actual ? "bg-foam text-pine-text" : "text-ink"
                }`}
              >
                {opcion.label}
              </Link>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
