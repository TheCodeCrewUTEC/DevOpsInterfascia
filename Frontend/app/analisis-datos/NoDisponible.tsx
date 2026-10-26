// Caja para lo que la plataforma todavía no puede mostrar (sin datos o sin fuente).

interface NoDisponibleProps {
  titulo?: string;
  motivo: string;
}

export default function NoDisponible({ titulo, motivo }: NoDisponibleProps) {
  return (
    <div className="rounded-3xl border-2 border-dashed border-ink/40 bg-sand p-5">
      {titulo ? <p className="text-base font-medium text-ink">{titulo}</p> : null}
      <p className={`text-sm text-ink/70 ${titulo ? "mt-1" : ""}`}>{motivo}</p>
    </div>
  );
}
