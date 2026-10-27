// Esqueleto mientras el servidor trae los datos de la vista: mismas cajas y medidas
// que la página real, así al llegar los datos nada salta de lugar.

const BLOQUE = "rounded-3xl border-2 border-ink/15 bg-paper";
const LINEA = "rounded-full bg-ink/10";

export default function CargandoAnalisis() {
  return (
    <main
      className="mx-auto flex w-full max-w-[100rem] flex-1 flex-col gap-6 px-6 py-10"
      role="status"
      aria-live="polite"
    >
      <span className="sr-only">Cargando el análisis de datos…</span>
      <div aria-hidden="true" className="flex flex-col gap-6 motion-safe:animate-pulse">
        <div className="flex flex-col gap-3">
          <div className={`${LINEA} h-3 w-24`} />
          <div className={`${LINEA} h-9 w-72 max-w-full`} />
          <div className={`${LINEA} h-3 w-[28rem] max-w-full`} />
        </div>
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 5 }, (_, indice) => (
            <div key={indice} className={`${LINEA} h-10 w-28`} />
          ))}
        </div>
        <div className={`${BLOQUE} h-14 md:h-44`} />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
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
