// Esqueleto de "Mis alertas" (y de sus preferencias) con las medidas de la página real

const LINEA = "rounded-full bg-ink/10";

export default function CargandoAlertas() {
  return (
    <main
      className="mx-auto flex w-full max-w-[100rem] flex-1 flex-col gap-6 px-6 py-10"
      role="status"
      aria-live="polite"
    >
      <span className="sr-only">Cargando tus alertas…</span>
      <div aria-hidden="true" className="flex flex-col gap-6 motion-safe:animate-pulse">
        <div className="flex flex-col gap-3">
          <div className={`${LINEA} h-3 w-24`} />
          <div className={`${LINEA} h-9 w-56 max-w-full`} />
          <div className={`${LINEA} h-3 w-[26rem] max-w-full`} />
        </div>
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 4 }, (_, indice) => (
            <div key={indice} className={`${LINEA} h-10 w-28`} />
          ))}
        </div>
        <div className="flex flex-col gap-3">
          {Array.from({ length: 4 }, (_, indice) => (
            <div key={indice} className="h-24 rounded-3xl border-2 border-ink/15 bg-paper" />
          ))}
        </div>
      </div>
    </main>
  );
}
