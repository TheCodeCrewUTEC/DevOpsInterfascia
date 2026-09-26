const departamentos = [
  "Artigas",
  "Canelones",
  "Cerro Largo",
  "Colonia",
  "Durazno",
  "Flores",
  "Florida",
  "Lavalleja",
  "Maldonado",
  "Montevideo",
  "Paysandú",
  "Río Negro",
  "Rivera",
  "Rocha",
  "Salto",
  "San José",
  "Soriano",
  "Tacuarembó",
  "Treinta y Tres",
];

const tematicas = [
  "Innovación",
  "Tecnología",
  "Agricultura",
  "Salud",
  "Educación",
  "Energía",
  "Medio ambiente",
];

const resultados = [
  {
    tipo: "Convocatoria",
    icono: "📢",
    titulo: "Validación de Idea de Negocio",
    descripcion:
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vivamus at facilisis arcu, finibus auctor arcu. Aenean a ante nisi.",
    estado: "Abierto",
    detalle: "Cierre: 16/10/2026",
  },
  {
    tipo: "Proyecto",
    icono: "📄",
    titulo: "Validación de Idea de Negocio",
    descripcion:
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vivamus at facilisis arcu, finibus auctor arcu. Aenean a ante nisi.",
    estado: "Seguimiento",
    detalle: "Año: 2020",
  },
  {
    tipo: "Convocatoria",
    icono: "📢",
    titulo: "Fondos para I+D territorial",
    descripcion:
      "Phasellus eros mi, maximus et tellus vel, lacinia aliquet risus. Etiam faucibus laoreet placerat.",
    estado: "Abierto",
    detalle: "Cierre: 30/11/2026",
  },
];

const investigadores = [
  {
    nombre: "María Jesús Lopez",
    institucion: "UTEC",
    ocupacion: "Investigadora",
    area: "Biotecnología",
  },
  {
    nombre: "Benito Perez",
    institucion: "UDELAR",
    ocupacion: "Docente",
    area: "Ingeniería",
  },
  {
    nombre: "Ana Rodríguez",
    institucion: "CURE",
    ocupacion: "Estudiante",
    area: "Ciencias ambientales",
  },
];

const filtrosActivos = ["Proyectos", "Convocatorias", "Investigadores"];

export default function RepositorioPage() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-6 py-8">

      {/* Título */}
      <div className="flex items-center gap-4">
        <div className="h-px flex-1 bg-black" />
        <h1 className="text-2xl font-normal text-black">
          Repositorio Público
        </h1>
        <div className="h-px flex-1 bg-black" />
      </div>

      <p className="mt-3 text-center text-sm text-black">
        Toda la información, en un solo lugar...
      </p>

      {/* Búsqueda */}
      <div className="relative mt-6">
        <input
          type="search"
          placeholder="Buscar..."
          className="h-10 w-full border border-black bg-neutral-200 px-4 pr-10 text-sm outline-none"
        />
        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-lg">
          🔍
        </span>
      </div>

      {/* Filtros chips */}
      <div className="mt-4 flex flex-wrap items-center gap-3">
        {filtrosActivos.map((filtro) => (
          <button
            key={filtro}
            type="button"
            className="flex items-center gap-2 bg-neutral-400 px-3 py-1 text-sm text-black"
          >
            {filtro}
            <span aria-hidden="true">×</span>
          </button>
        ))}
        <button type="button" className="text-sm text-black underline">
          Agregar Filtros...
        </button>
      </div>

      {/* Selects */}
      <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="flex flex-col gap-1">
          <label htmlFor="territorio" className="text-xs text-black">
            Territorio
          </label>
          <select
            id="territorio"
            className="h-9 border border-black bg-neutral-200 px-2 text-sm outline-none"
            defaultValue=""
          >
            <option value="" disabled>
              Selecciona un departamento...
            </option>
            {departamentos.map((departamento) => (
              <option key={departamento} value={departamento}>
                {departamento}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="tematica" className="text-xs text-black">
            Temática
          </label>
          <select
            id="tematica"
            className="h-9 border border-black bg-neutral-200 px-2 text-sm outline-none"
            defaultValue=""
          >
            <option value="" disabled>
              Selecciona un Tema...
            </option>
            {tematicas.map((tematica) => (
              <option key={tematica} value={tematica}>
                {tematica}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Resultados + sidebar */}
      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-[2fr_1fr]">

        {/* Cards */}
        <div className="flex flex-col gap-4">
          {resultados.map((item) => (
            <article
              key={`${item.tipo}-${item.titulo}-${item.detalle}`}
              className="flex gap-4 bg-neutral-500 p-4 text-white"
            >
              <div className="flex h-12 w-12 shrink-0 items-center justify-center bg-neutral-700 text-2xl">
                {item.icono}
              </div>

              <div className="min-w-0 flex-1">
                <h2 className="text-base font-semibold">
                  “{item.titulo}”
                </h2>
                <p className="mt-2 text-xs leading-relaxed text-neutral-100">
                  <span className="font-semibold">Descripción:</span>{" "}
                  {item.descripcion}
                </p>
              </div>

              <div className="hidden shrink-0 text-right text-xs sm:block">
                <p>
                  <span className="font-semibold">Tipo:</span> {item.tipo}
                </p>
                <p className="mt-1">
                  <span className="font-semibold">Estado:</span> {item.estado}
                </p>
                <p className="mt-1">{item.detalle}</p>
              </div>
            </article>
          ))}
        </div>

        {/* Investigadores */}
        <aside className="bg-neutral-500 p-4 text-white">
          <div className="flex flex-col gap-5">
            {investigadores.map((persona) => (
              <div key={persona.nombre} className="flex gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-neutral-700 text-lg">
                  👤
                </div>
                <div className="text-xs leading-relaxed">
                  <p className="text-sm font-semibold">{persona.nombre}</p>
                  <p>
                    <span className="font-semibold">Institución:</span>{" "}
                    {persona.institucion}
                  </p>
                  <p>
                    <span className="font-semibold">Ocupación:</span>{" "}
                    {persona.ocupacion}
                  </p>
                  <p>
                    <span className="font-semibold">Área:</span> {persona.area}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </aside>

      </div>

    </main>
  );
}
