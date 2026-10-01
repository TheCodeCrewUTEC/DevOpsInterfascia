import Link from "next/link";
import { cookies } from "next/headers";
import SesionMenu from "./SesionMenu";

const links = [
  { href: "/repositorio", label: "Repositorio" },
  { href: "/#que-es-interfascia", label: "¿Qué es Interfascia?" },
  { href: "/consultor-ia", label: "Consultor IA" },
  { href: "/analisis-datos", label: "Análisis de Datos" },
];

export default async function Navbar() {
  const sesion = (await cookies()).get("sesion")?.value;
  let usuario: string | null = null;

  if (sesion) {
    try {
      usuario = decodeURIComponent(sesion);
    } catch {
      usuario = sesion;
    }
  }
  return (
    <nav className="sticky top-0 z-50 border-b border-pine/10 bg-sand/80 px-6 py-4 backdrop-blur-md">
      <div className="mx-auto grid max-w-6xl grid-cols-[1fr_auto] items-center gap-x-4 gap-y-3 md:grid-cols-[1fr_auto_1fr]">
        <Link href="/" className="flex shrink-0 items-center gap-3 justify-self-start">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-pine text-ink">
            <Mark />
          </span>
          <span className="font-display text-xl tracking-tight text-ink">
            Interfascia
          </span>
        </Link>

        <div className="col-span-2 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-center md:col-span-1 md:col-start-2 md:row-start-1 md:flex-nowrap">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="nav-link text-xs text-ink/80 transition-colors hover:text-pine sm:text-sm md:whitespace-nowrap"
            >
              {link.label}
            </Link>
          ))}
        </div>

        <div className="col-start-2 row-start-1 flex shrink-0 items-center justify-end justify-self-end gap-3 max-md:[&_a]:whitespace-nowrap max-md:[&_a]:px-3 max-md:[&_a]:py-1.5 max-md:[&_a]:text-xs max-md:[&_button]:whitespace-nowrap max-md:[&_button]:px-3 max-md:[&_button]:py-1.5 max-md:[&_button]:text-xs md:col-start-3">
          <SesionMenu usuarioInicial={usuario} />
        </div>
      </div>
    </nav>
  );
}

function Mark() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <circle cx="5" cy="9" r="2.2" fill="currentColor" />
      <circle cx="13" cy="5" r="2.2" fill="#f26b3a" />
      <circle cx="13" cy="13" r="2.2" fill="#ffffff" />
      <path d="M7 8.2 11 5.8M7 9.8 11 12.2" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}
