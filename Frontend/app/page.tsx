import Link from "next/link";

const caminos = [
  {
    href: "/repositorio",
    kicker: "Consultar",
    titulo: "Repositorio",
    texto:
      "Convocatorias, proyectos e investigadores reunidos para buscarlos en un solo lugar.",
    accion: "Abrir repositorio",
  },
  {
    href: "/consultor-ia",
    kicker: "Relacionar",
    titulo: "Consultor IA",
    texto:
      "Contá de qué trata tu proyecto y encontrá fondos, antecedentes y personas afines.",
    accion: "Usar el consultor",
  },
  {
    href: "/analisis-datos",
    kicker: "Leer el territorio",
    titulo: "Análisis de datos",
    texto:
      "Un espacio para mirar patrones de financiamiento y capacidades de investigación.",
    accion: "Ver el módulo",
  },
];

const vinculos = [
  {
    titulo: "Proyecto",
    texto: "Una idea con territorio, equipo y una necesidad concreta.",
  },
  {
    titulo: "Fondo",
    texto: "Convocatorias abiertas, requisitos y plazos de cierre.",
  },
  {
    titulo: "Investigación",
    texto: "Personas e instituciones con trayectoria en el tema.",
  },
];

export default function Home() {
  return (
    <main>
      <section className="relative overflow-hidden px-6 pb-16 pt-12 sm:pt-16">
        <div className="blob pointer-events-none absolute -left-16 top-8 h-56 w-56 rounded-full bg-gold/50 blur-3xl" />
        <div className="blob-late pointer-events-none absolute right-0 top-24 h-64 w-64 rounded-full bg-pine/20 blur-3xl" />

        <div className="relative mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <p className="rise text-sm font-medium tracking-[0.18em] text-clay uppercase">
              Plataforma piloto · Uruguay
            </p>
            <h1 className="rise rise-1 font-display mt-4 max-w-xl text-5xl leading-[1.05] text-ink sm:text-6xl">
              Impulsando la innovación en el territorio uruguayo
            </h1>
            <p className="rise rise-2 mt-6 max-w-xl text-lg leading-relaxed text-ink/75">
              Interfascia conecta proyectos, fondos y capacidades de investigación
              para que una idea del territorio encuentre con quién y con qué seguir.
            </p>
            <div className="rise rise-3 mt-8 flex flex-wrap gap-3">
              <Link
                href="/repositorio"
                className="rounded-full bg-pine px-5 py-3 text-sm font-medium text-ink shadow-sm transition duration-200 hover:-translate-y-0.5 hover:bg-pine-hover"
              >
                Explorar el repositorio
              </Link>
              <Link
                href="/consultor-ia"
                className="rounded-full border border-ink/15 bg-paper px-5 py-3 text-sm text-ink transition duration-200 hover:-translate-y-0.5 hover:border-pine hover:text-pine"
              >
                Contar mi proyecto
              </Link>
            </div>
          </div>

          <Territorio />
        </div>
      </section>

      <section id="que-es-interfascia" className="scroll-mt-24 px-6 py-16">
        <div className="mx-auto max-w-6xl">
          <div className="rise flex items-center gap-4">
            <div className="h-px flex-1 bg-pine/20" />
            <h2 className="font-display text-3xl text-ink">¿Qué es Interfascia?</h2>
            <div className="h-px flex-1 bg-pine/20" />
          </div>

          <p className="rise rise-1 mx-auto mt-8 max-w-3xl text-center text-lg leading-relaxed text-ink/75">
            Es un piloto para facilitar la vinculación entre proyectos, inversores,
            fondos y capacidades de investigación en Uruguay. La información deja de
            estar repartida y pasa a poder consultarse, compararse y relacionarse.
          </p>

          <div className="mt-12 grid gap-5 md:grid-cols-3">
            {caminos.map((camino, index) => (
              <Link
                key={camino.href}
                href={camino.href}
                className={`rise rise-${index + 1} group flex flex-col rounded-3xl border border-pine/10 bg-paper p-6 shadow-sm transition duration-300 hover:-translate-y-1.5 hover:border-pine/30 hover:shadow-lg`}
              >
                <span className="text-xs font-medium tracking-[0.16em] text-clay uppercase">
                  {camino.kicker}
                </span>
                <h3 className="font-display mt-3 text-2xl text-ink">{camino.titulo}</h3>
                <p className="mt-3 flex-1 text-sm leading-relaxed text-ink/70">
                  {camino.texto}
                </p>
                <span className="mt-6 text-sm text-pine-text transition-transform duration-200 group-hover:translate-x-1">
                  {camino.accion} →
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="px-6 pb-20">
        <div className="mx-auto max-w-6xl rounded-[2rem] bg-pine-deep px-6 py-10 text-paper sm:px-10">
          <h2 className="font-display text-3xl">Cómo se vincula</h2>
          <p className="mt-3 max-w-2xl text-paper/75">
            El recorrido de la plataforma une la idea, el financiamiento y quién puede llevarla adelante.
          </p>
          <ol className="mt-8 grid gap-4 md:grid-cols-3">
            {vinculos.map((item, index) => (
              <li
                key={item.titulo}
                className="rounded-2xl bg-white/10 p-5 ring-1 ring-white/15 transition duration-300 hover:bg-white/20"
              >
                <span className="font-display text-gold text-lg">0{index + 1}</span>
                <h3 className="mt-2 text-xl">{item.titulo}</h3>
                <p className="mt-2 text-sm leading-relaxed text-paper/75">{item.texto}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>
    </main>
  );
}

function Territorio() {
  return (
    <div className="rise rise-2 relative mx-auto h-[420px] w-full max-w-md">
      <div className="absolute inset-6 rounded-[2rem] bg-foam/80 ring-1 ring-pine/10" />

      <svg
        viewBox="0 0 360 420"
        className="absolute inset-0 h-full w-full"
        aria-hidden="true"
      >
        <path
          className="draw-line"
          d="M90 120 C150 120, 170 190, 230 180"
          fill="none"
          stroke="#00aeef"
          strokeWidth="2"
          pathLength="1"
        />
        <path
          className="draw-line"
          d="M90 280 C160 270, 180 220, 240 250"
          fill="none"
          stroke="#f26b3a"
          strokeWidth="2"
          pathLength="1"
          style={{ animationDelay: "0.25s" }}
        />
        <path
          className="draw-line"
          d="M230 190 C250 210, 250 230, 242 246"
          fill="none"
          stroke="#07324a"
          strokeWidth="2"
          pathLength="1"
          style={{ animationDelay: "0.45s" }}
        />
        <circle className="pulse-node" cx="84" cy="116" r="8" fill="#00aeef" />
        <circle className="pulse-node" cx="236" cy="176" r="8" fill="#07324a" style={{ animationDelay: "0.4s" }} />
        <circle className="pulse-node" cx="246" cy="258" r="8" fill="#f26b3a" style={{ animationDelay: "0.8s" }} />
      </svg>

      <article className="float-slow absolute left-4 top-10 w-44 rounded-2xl bg-paper p-4 shadow-md ring-1 ring-pine/10">
        <p className="text-xs tracking-wide text-pine-text uppercase">Proyecto</p>
        <p className="font-display mt-1 text-lg leading-tight text-ink">Idea en el territorio</p>
      </article>

      <article className="float-slow-late absolute right-3 top-36 w-44 rounded-2xl bg-pine p-4 text-ink shadow-md">
        <p className="text-xs tracking-wide text-ink/70 uppercase">Fondo</p>
        <p className="font-display mt-1 text-lg leading-tight">Convocatoria abierta</p>
      </article>

      <article className="float-slow absolute bottom-8 left-10 w-48 rounded-2xl bg-paper p-4 shadow-md ring-1 ring-clay/20" style={{ animationDelay: "0.4s" }}>
        <p className="text-xs tracking-wide text-clay uppercase">Investigación</p>
        <p className="font-display mt-1 text-lg leading-tight text-ink">Quién puede sumarse</p>
      </article>
    </div>
  );
}
