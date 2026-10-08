import Link from "next/link";

const pestanas = [
  { href: "/consultor-ia/relacionar", id: "relacionar", label: "Relacionar" },
  { href: "/consultor-ia/postular", id: "postular", label: "Postular" },
] as const;

export default function Pestanas({ actual }: { actual: "relacionar" | "postular" }) {
  return (
    <nav className="mt-6 flex flex-wrap gap-2" aria-label="Consultor IA">
      {pestanas.map((pestana) => {
        const activa = pestana.id === actual;
        return (
          <Link
            key={pestana.id}
            href={pestana.href}
            aria-current={activa ? "page" : undefined}
            className={
              activa
                ? "rounded-full bg-pine px-4 py-2 text-sm font-medium text-ink"
                : "rounded-full border border-pine/30 bg-paper px-4 py-2 text-sm text-ink/80 transition hover:border-pine hover:text-ink"
            }
          >
            {pestana.label}
          </Link>
        );
      })}
    </nav>
  );
}
