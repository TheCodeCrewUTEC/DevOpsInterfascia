type LoadingProps = {
  mensaje: string;
};

export default function Loading({ mensaje }: LoadingProps) {
  return (
    <main
      className="flex flex-1 flex-col items-center justify-center px-6 py-24"
      role="status"
      aria-live="polite"
    >
      <div className="flex h-20 w-20 items-center justify-center rounded-full bg-foam">
        <span
          className="h-10 w-10 animate-spin rounded-full border-4 border-pine/25 border-t-pine motion-reduce:animate-none"
          aria-hidden="true"
        />
      </div>
      <h1 className="mt-8 text-center font-display text-3xl text-ink">
        Generando las respuestas
      </h1>
      <p className="mt-3 max-w-md text-center text-sm leading-relaxed text-ink/80">
        {mensaje}
      </p>
      <p className="mt-2 max-w-md text-center text-sm leading-relaxed text-ink/60">
        Consultamos el estado del formulario cada 5 segundos.
      </p>
    </main>
  );
}
