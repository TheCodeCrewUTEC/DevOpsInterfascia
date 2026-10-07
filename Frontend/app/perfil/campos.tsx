export const ESTILO_INPUT =
  "h-11 w-full rounded-xl border border-pine/20 bg-foam/70 px-4 text-sm text-ink outline-none transition focus:border-pine focus:bg-paper disabled:cursor-not-allowed disabled:opacity-70";

export function Campo({
  id,
  label,
  requerido = false,
  ayuda,
  children,
}: {
  id: string;
  label: string;
  requerido?: boolean;
  ayuda?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm text-ink">
        {label}
        {requerido ? "*" : ""}
      </label>
      {children}
      {ayuda ? <p className="text-xs text-ink/50">{ayuda}</p> : null}
    </div>
  );
}

export function Aviso({ ok, texto }: { ok: boolean; texto: string }) {
  return (
    <p
      role={ok ? "status" : "alert"}
      className={
        ok
          ? "rounded-2xl border border-pine/30 bg-foam px-4 py-3 text-sm text-ink"
          : "rounded-2xl border border-clay/30 bg-clay/10 px-4 py-3 text-sm text-ink"
      }
    >
      {texto}
    </p>
  );
}
