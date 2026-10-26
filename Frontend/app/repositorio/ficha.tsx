import Link from "next/link";
import type { ReactNode } from "react";

export function texto(valor: string | null | undefined) {
  const limpio = valor?.trim();
  return limpio ? limpio : "Sin dato";
}

export function fecha(valor: string | null | undefined) {
  if (!valor) return "Sin fecha";
  const [anio, mes, dia] = valor.slice(0, 10).split("-");
  if (!anio || !mes || !dia) return valor;
  return `${dia}/${mes}/${anio}`;
}

export function pesos(valor: number | string | null | undefined) {
  if (valor == null || valor === "") return "Sin monto";
  const numero = typeof valor === "number" ? valor : Number(valor);
  if (!Number.isFinite(numero)) return "Sin monto";
  return `$U ${new Intl.NumberFormat("es-UY", { maximumFractionDigits: 0 }).format(numero)}`;
}

export function enlaceFuente(url: string | null | undefined) {
  if (!url || !/^https?:\/\//i.test(url.trim())) return null;
  let host = "";
  try {
    host = new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
  const etiqueta = host.includes("ande.org")
    ? "Página de la convocatoria"
    : host.includes("anii.org") || host.includes("sni.org")
      ? "CV en CVUy"
      : host;
  return { href: url.trim(), etiqueta };
}

export function Volver({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className="text-sm text-pine-text transition hover:text-ink">
      {children}
    </Link>
  );
}

export function Seccion({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className="rounded-3xl border border-pine/10 bg-paper p-6 shadow-sm">
      <h2 className="text-sm font-medium tracking-[0.16em] text-pine-text uppercase">{titulo}</h2>
      <div className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-ink/80">{children}</div>
    </section>
  );
}
