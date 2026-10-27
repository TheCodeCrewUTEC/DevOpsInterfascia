// Esqueleto de las métricas de uso con las mismas medidas que la página real

const BLOQUE = "rounded-3xl border-2 border-ink/15 bg-paper";
const LINEA = "rounded-full bg-ink/10";

export default function CargandoMetricas() {
  return (
    <main
      className="mx-auto flex w-full max-w-[100rem] flex-1 flex-col gap-6 px-6 py-10"
      role="status"
      aria-live="polite"
    >
      <span className="sr-only">Cargando las métricas de uso…</span>
      <div aria-hidden="true" className="flex flex-col gap-6 motion-safe:animate-pulse">
        <div className="flex flex-col gap-3">
          <div className={`${LINEA} h-3 w-32`} />
          <div className={`${LINEA} h-9 w-64 max-w-full`} />
          <div className={`${LINEA} h-3 w-[30rem] max-w-full`} />
        </div>
        <div className={`${BLOQUE} h-28`} />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }, (_, indice) => (
            <div key={indice} className={`${BLOQUE} h-32`} />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className={`${BLOQUE} h-72`} />
          <div className={`${BLOQUE} h-72`} />
        </div>
      </div>
    </main>
  );
}
