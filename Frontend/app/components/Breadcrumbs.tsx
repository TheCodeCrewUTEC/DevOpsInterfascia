"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// Nombre y destino de cada segmento de la URL. href null = sección sin página propia.
const SEGMENTOS: Record<string, { label: string; href?: string | null }> = {
  repositorio: { label: "Repositorio" },
  "consultor-ia": { label: "Consultor IA", href: "/consultor-ia/relacionar" },
  relacionar: { label: "Relacionar" },
  postular: { label: "Postular" },
  "analisis-datos": { label: "Análisis de Datos" },
  perfil: { label: "Mi perfil" },
  contrasena: { label: "Contraseña" },
  admin: { label: "Administración", href: null },
  usuarios: { label: "Usuarios" },
  registro: { label: "Registro", href: null },
  confirmado: { label: "Confirmado" },
};

export default function Breadcrumbs() {
  const ruta = usePathname();
  const partes = ruta.split("/").filter(Boolean);

  // En el inicio no hace falta: ya es la raíz
  if (partes.length === 0) return null;

  const migas = partes.map((parte, indice) => {
    const conocido = SEGMENTOS[parte];
    const hrefPorDefecto = `/${partes.slice(0, indice + 1).join("/")}`;
    return {
      label: conocido?.label ?? decodeURIComponent(parte),
      href: conocido?.href === undefined ? hrefPorDefecto : conocido.href,
    };
  });

  return (
    <nav aria-label="Ruta de navegación" className="px-6 pt-4">
      <ol className="mx-auto flex max-w-[100rem] flex-wrap items-center gap-1.5 text-sm text-ink/70">
        <li>
          <Link href="/" className="transition hover:text-pine-text hover:underline">
            Inicio
          </Link>
        </li>
        {migas.map((miga, indice) => {
          const ultima = indice === migas.length - 1;
          return (
            <li key={`${miga.label}-${indice}`} className="flex items-center gap-1.5">
              <span aria-hidden="true" className="text-ink/40">
                /
              </span>
              {ultima ? (
                <span aria-current="page" className="font-medium text-ink">
                  {miga.label}
                </span>
              ) : miga.href ? (
                <Link href={miga.href} className="transition hover:text-pine-text hover:underline">
                  {miga.label}
                </Link>
              ) : (
                <span>{miga.label}</span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
