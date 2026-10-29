// Esqueleto de las preferencias de alertas: las dos cajas de la página real

const LINEA = "rounded-full bg-ink/10";

export default function CargandoPreferencias() {
  return (
    <main
      className="mx-auto flex w-full max-w-[100rem] flex-1 flex-col gap-6 px-6 py-10"
      role="status"
      aria-live="polite"
    >
      <span className="sr-only">Cargando tus preferencias…</span>
      <div aria-hidden="true" className="flex flex-col gap-6 motion-safe:animate-pulse">
        <div className="flex flex-col gap-3">
          <div className={`${LINEA} h-3 w-24`} />
          <div className={`${LINEA} h-9 w-80 max-w-full`} />
          <div className={`${LINEA} h-3 w-[30rem] max-w-full`} />
        </div>
        <div className="grid gap-6 lg:grid-cols-2 lg:items-start">
          <div className="h-96 rounded-3xl border-2 border-ink/15 bg-paper" />
          <div className="h-96 rounded-3xl border-2 border-ink/15 bg-paper" />
        </div>
      </div>
    </main>
  );
}
