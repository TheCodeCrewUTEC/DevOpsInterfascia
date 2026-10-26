"use client";

import Link from "next/link";
import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";

type Opcion = { id: string; label: string };

type Opciones = {
  estados: string[];
  instituciones: string[];
  beneficiarios: Opcion[];
  tematicas: Opcion[];
  departamentos: string[];
  regiones: Opcion[];
};

const opcionesIniciales: Opciones = {
  estados: ["Abierta", "Cerrada"],
  instituciones: [],
  beneficiarios: [
    { id: "mipymes", label: "Mipymes" },
    { id: "grandes", label: "Grandes empresas" },
    { id: "instituciones", label: "Instituciones y cámaras" },
    { id: "personas", label: "Personas y emprendedores" },
    { id: "cooperativas", label: "Cooperativas" },
    { id: "turismo", label: "Sector turístico" },
    { id: "productores", label: "Productores" },
  ],
  tematicas: [
    { id: "innovacion", label: "Innovación" },
    { id: "tecnologia", label: "Tecnología y digital" },
    { id: "agro", label: "Agro y pesca" },
    { id: "economia_circular", label: "Economía circular" },
    { id: "turismo", label: "Turismo" },
    { id: "audiovisual", label: "Audiovisual" },
    { id: "territorial", label: "Desarrollo territorial" },
    { id: "energia", label: "Energía" },
    { id: "salud", label: "Salud" },
    { id: "educacion", label: "Educación y formación" },
    { id: "medio_ambiente", label: "Medio ambiente" },
  ],
  departamentos: [
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
  ],
  regiones: [
    { id: "este", label: "Este" },
    { id: "sur", label: "Sur" },
    { id: "litoral", label: "Litoral" },
    { id: "noreste", label: "Noreste" },
    { id: "norte", label: "Norte" },
    { id: "centro", label: "Centro" },
  ],
};

type FiltrosConvocatoria = {
  estado: string;
  institucion: string;
  beneficiario: string;
  tematica: string;
  alcance: "" | "todo_uruguay" | "departamento" | "localidad" | "region";
  ubicacion: string;
  montoMin: string;
  montoMax: string;
  plazo: "" | "apertura" | "cierre" | "proximas";
  fechaDesde: string;
  fechaHasta: string;
};

const filtrosVacios: FiltrosConvocatoria = {
  estado: "",
  institucion: "",
  beneficiario: "",
  tematica: "",
  alcance: "",
  ubicacion: "",
  montoMin: "",
  montoMax: "",
  plazo: "",
  fechaDesde: "",
  fechaHasta: "",
};

const secciones = ["Proyectos", "Convocatorias", "Investigadores"] as const;

type Filtro = (typeof secciones)[number];

type Convocatoria = {
  id: number;
  titulo: string | null;
  institucion: string | null;
  estado: string | null;
  fecha_apertura: string | null;
  fecha_cierre: string | null;
  descripcion: string | null;
  financiamiento: number | string | null;
};

type ConvocatoriasResponse = {
  items: Convocatoria[];
  total_pages: number;
};

type Proyecto = {
  id: number;
  nombre: string | null;
  estado: string | null;
  anio: string | null;
  descripcion: string | null;
};

type Investigador = {
  id: number;
  nombre: string | null;
  apellido: string | null;
  institucion: string | null;
  titulo: string | null;
  investigaciones: string | null;
  nivel_sni: string | null;
  categoria_sni: string | null;
};

type Tarjeta = {
  key: string;
  href: string | null;
  tipo: "Convocatoria" | "Proyecto";
  titulo: string;
  descripcion: string;
  estado: string;
  detalle: string;
  financiamiento: string | null;
  texto: string;
};

const chevron =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='none' stroke='%23102a3c' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M5 7.5 10 12.5 15 7.5'/%3E%3C/svg%3E\")";

const campoSelect =
  "h-11 w-full appearance-none rounded-xl border border-pine/20 bg-foam/70 bg-[length:16px] bg-[position:right_1rem_center] bg-no-repeat px-4 pr-12 text-sm text-ink outline-none transition focus:border-pine focus:bg-paper";

function texto(valor: string | null | undefined, vacio = "—") {
  const limpio = valor?.trim();
  return limpio ? limpio : vacio;
}

function pesos(valor: number | string | null | undefined) {
  if (valor == null || valor === "") return null;
  const numero = typeof valor === "number" ? valor : Number(valor);
  if (!Number.isFinite(numero)) return null;
  return `$U ${new Intl.NumberFormat("es-UY", { maximumFractionDigits: 0 }).format(numero)}`;
}

function detalleFecha(item: { fecha_apertura: string | null; fecha_cierre: string | null }) {
  if (item.fecha_cierre) return `Cierre: ${formatFecha(item.fecha_cierre)}`;
  if (item.fecha_apertura) return `Apertura: ${formatFecha(item.fecha_apertura)}`;
  return "Sin fecha";
}

function formatFecha(valor: string | null) {
  if (!valor) return "Sin fecha";
  const [anio, mes, dia] = valor.slice(0, 10).split("-");
  if (!anio || !mes || !dia) return valor;
  return `${dia}/${mes}/${anio}`;
}

function campo(valor: string | null | undefined, vacio: string) {
  const limpio = valor?.trim();
  if (!limpio) return vacio;
  return limpio.length <= 50 ? limpio : `${limpio.slice(0, 49)}…`;
}

function primerTermino(valor: string | null | undefined) {
  return valor?.trim().split(/\s+/)[0] ?? "";
}

function nombreCorto(persona: Investigador) {
  return campo(
    [primerTermino(persona.nombre), primerTermino(persona.apellido)].filter(Boolean).join(" "),
    "Sin nombre",
  );
}

function enunciado(valor: string | null | undefined) {
  const primera = valor
    ?.split(/\r?\n/)
    .map((linea) => linea.trim())
    .find(Boolean);
  if (!primera) return null;
  const fin = primera.search(/[.!?](?:\s|$)/);
  return fin >= 0 ? primera.slice(0, fin + 1) : primera;
}

async function leerJson<T>(response: Response, recurso: string): Promise<T> {
  if (!response.ok) {
    let detalle = "";
    try {
      const cuerpo = (await response.json()) as { detail?: unknown };
      if (typeof cuerpo.detail === "string") detalle = cuerpo.detail;
    } catch {
      detalle = "";
    }
    throw new Error(detalle || `No se pudieron cargar ${recurso} (${response.status}).`);
  }
  return response.json() as Promise<T>;
}

function consultaConvocatorias(busqueda: string, filtros: FiltrosConvocatoria) {
  const params = new URLSearchParams({ limit: "100" });
  const texto = busqueda.trim();
  if (texto) params.set("buscar", texto);
  if (filtros.estado) params.set("estado", filtros.estado);
  if (filtros.institucion) params.set("institucion", filtros.institucion);
  if (filtros.beneficiario) params.set("beneficiario", filtros.beneficiario);
  if (filtros.tematica) params.set("tematica", filtros.tematica);

  if (filtros.alcance === "todo_uruguay") {
    params.set("alcance", "todo_uruguay");
  } else if (filtros.alcance && filtros.ubicacion.trim().length >= 2) {
    params.set("alcance", filtros.alcance);
    params.set("ubicacion", filtros.ubicacion.trim());
  }

  const minimo = filtros.montoMin.trim();
  const maximo = filtros.montoMax.trim();
  const montosInvalidos = minimo !== "" && maximo !== "" && Number(minimo) > Number(maximo);
  if (!montosInvalidos) {
    if (minimo) params.set("financiamiento_min", minimo);
    if (maximo) params.set("financiamiento_max", maximo);
  }

  if (filtros.plazo === "proximas") {
    params.set("proximas_a_abrir", "true");
  } else if (filtros.plazo === "apertura" || filtros.plazo === "cierre") {
    const desde = filtros.plazo === "apertura" ? "fecha_apertura_desde" : "fecha_cierre_desde";
    const hasta = filtros.plazo === "apertura" ? "fecha_apertura_hasta" : "fecha_cierre_hasta";
    if (filtros.fechaDesde) params.set(desde, filtros.fechaDesde);
    if (filtros.fechaHasta) params.set(hasta, filtros.fechaHasta);
  }

  return { params, montosInvalidos };
}

async function cargarConvocatorias(params: URLSearchParams, signal: AbortSignal) {
  const items: Convocatoria[] = [];
  let pagina = 1;
  let totalPaginas = 1;

  while (pagina <= totalPaginas && pagina <= 5) {
    const consulta = new URLSearchParams(params);
    consulta.set("page", String(pagina));
    const response = await fetch(`${API_URL}/api/convocatorias/?${consulta}`, { signal });
    const datos = await leerJson<ConvocatoriasResponse>(response, "las convocatorias");
    items.push(...datos.items);
    totalPaginas = datos.total_pages || 1;
    pagina += 1;
  }

  return items;
}

export default function RepositorioPage() {
  const [consulta, setConsulta] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const [filtros, setFiltros] = useState<FiltrosConvocatoria>(filtrosVacios);
  const [opciones, setOpciones] = useState<Opciones>(opcionesIniciales);
  const [activos, setActivos] = useState<Filtro[]>([...secciones]);
  const [tarjetas, setTarjetas] = useState<Tarjeta[]>([]);
  const [personas, setPersonas] = useState<Investigador[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controlador = new AbortController();

    async function cargarOpciones() {
      try {
        const response = await fetch(`${API_URL}/api/convocatorias/opciones`, {
          signal: controlador.signal,
        });
        if (!response.ok) return;
        const datos = (await response.json()) as Opciones;
        if (datos.estados?.length) setOpciones(datos);
      } catch {
        // Quedan las opciones locales si el listado de filtros no responde.
      }
    }

    void cargarOpciones();
    return () => controlador.abort();
  }, []);

  useEffect(() => {
    const controlador = new AbortController();

    async function cargar() {
      setCargando(true);
      setError(null);

      const { params: paramsConvocatoria } = consultaConvocatorias(busqueda, filtros);
      const params = new URLSearchParams({ limit: "50" });
      if (busqueda.trim()) params.set("buscar", busqueda.trim());
      const query = params.toString();

      try {
        const convocatorias = await cargarConvocatorias(paramsConvocatoria, controlador.signal);
        const [proyectosRes, investigadoresRes] = await Promise.all([
          fetch(`${API_URL}/api/proyectos/?${query}`, { signal: controlador.signal }),
          fetch(`${API_URL}/api/investigadores/?${query}`, { signal: controlador.signal }),
        ]);

        const [proyectos, investigadores] = await Promise.all([
          leerJson<Proyecto[]>(proyectosRes, "los proyectos"),
          leerJson<Investigador[]>(investigadoresRes, "los investigadores"),
        ]);

        setTarjetas([
          ...convocatorias.map((item) => ({
            key: `convocatoria-${item.id}`,
            href: `/repositorio/convocatorias/${item.id}`,
            tipo: "Convocatoria" as const,
            titulo: texto(item.titulo, "Sin título"),
            descripcion: texto(item.descripcion, "Sin descripción"),
            estado: texto(item.estado, "Sin estado"),
            detalle: detalleFecha(item),
            financiamiento: pesos(item.financiamiento),
            texto: [item.titulo, item.descripcion, item.estado, item.institucion].filter(Boolean).join(" "),
          })),
          ...proyectos.map((item) => ({
            key: `proyecto-${item.id}`,
            href: null,
            tipo: "Proyecto" as const,
            titulo: texto(item.nombre, "Sin nombre"),
            descripcion: texto(item.descripcion, "Sin descripción"),
            estado: texto(item.estado, "Sin estado"),
            detalle: `Año: ${texto(item.anio)}`,
            financiamiento: null,
            texto: [item.nombre, item.descripcion, item.estado, item.anio].filter(Boolean).join(" "),
          })),
        ]);
        setPersonas(investigadores);
      } catch (err) {
        if (controlador.signal.aborted) return;
        setTarjetas([]);
        setPersonas([]);
        const mensaje = err instanceof Error ? err.message : "";
        setError(
          mensaje && mensaje !== "Failed to fetch"
            ? mensaje
            : "No se pudo conectar con el backend.",
        );
      } finally {
        if (!controlador.signal.aborted) setCargando(false);
      }
    }

    void cargar();
    return () => controlador.abort();
  }, [busqueda, filtros]);

  const visibles = useMemo(
    () =>
      tarjetas.filter((item) => {
        if (item.tipo === "Proyecto" && !activos.includes("Proyectos")) return false;
        if (item.tipo === "Convocatoria" && !activos.includes("Convocatorias")) return false;
        return true;
      }),
    [tarjetas, activos],
  );

  const investigadores = personas;

  function cambiarFiltro<K extends keyof FiltrosConvocatoria>(clave: K, valor: FiltrosConvocatoria[K]) {
    setFiltros((actual) => ({ ...actual, [clave]: valor }));
  }

  function buscar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusqueda(consulta);
  }

  function quitarFiltro(filtro: Filtro) {
    setActivos((actual) => actual.filter((item) => item !== filtro));
  }

  function agregarFiltro(filtro: Filtro) {
    setActivos((actual) => (actual.includes(filtro) ? actual : [...actual, filtro]));
  }

  const mostrarResultados = activos.includes("Proyectos") || activos.includes("Convocatorias");
  const mostrarPersonas = activos.includes("Investigadores");
  const inactivos = secciones.filter((filtro) => !activos.includes(filtro));

  return (
    <main>
      <section className="relative overflow-hidden px-6 pb-8 pt-12 sm:pt-16">
        <div className="blob pointer-events-none absolute -left-16 top-8 h-56 w-56 rounded-full bg-gold/50 blur-3xl" />
        <div className="blob-late pointer-events-none absolute right-0 top-16 h-64 w-64 rounded-full bg-pine/20 blur-3xl" />

        <div className="relative mx-auto max-w-6xl">
          <p className="rise text-sm font-medium tracking-[0.18em] text-clay uppercase">
            Consultar · Uruguay
          </p>
          <h1 className="rise rise-1 font-display mt-4 text-5xl leading-[1.05] text-ink sm:text-6xl">
            Repositorio público
          </h1>
          <p className="rise rise-2 mt-6 max-w-2xl text-lg leading-relaxed text-ink/75">
            Convocatorias, proyectos e investigadores reunidos para buscarlos en un solo lugar.
          </p>

          <form onSubmit={buscar} className="rise rise-3 relative mt-8">
            <label htmlFor="buscar-repositorio" className="sr-only">
              Buscar en el repositorio
            </label>
            <input
              id="buscar-repositorio"
              type="search"
              value={consulta}
              onChange={(event) => setConsulta(event.target.value)}
              placeholder="Buscar convocatorias, proyectos o personas..."
              className="h-12 w-full rounded-full border border-pine/20 bg-paper px-5 pr-14 text-sm text-ink shadow-sm outline-none transition focus:border-pine"
            />
            <button
              type="submit"
              className="absolute top-1/2 right-2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full bg-pine text-ink transition hover:bg-pine-hover"
              aria-label="Buscar"
            >
              <Lupa />
            </button>
          </form>

          <div className="rise rise-4 mt-5 flex flex-wrap items-center gap-2">
            {activos.map((filtro) => (
              <button
                key={filtro}
                type="button"
                onClick={() => quitarFiltro(filtro)}
                className="flex items-center gap-2 rounded-full bg-pine px-3 py-1.5 text-sm text-ink transition hover:bg-pine-hover"
              >
                {filtro}
                <span aria-hidden="true">×</span>
                <span className="sr-only">Quitar filtro {filtro}</span>
              </button>
            ))}
            {inactivos.map((filtro) => (
              <button
                key={filtro}
                type="button"
                onClick={() => agregarFiltro(filtro)}
                className="rounded-full border border-ink/15 bg-paper px-3 py-1.5 text-sm text-ink/70 transition hover:border-pine hover:text-pine-text"
              >
                Agregar {filtro.toLowerCase()}
              </button>
            ))}
          </div>

          <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Campo label="Estado" id="estado">
              <select
                id="estado"
                value={filtros.estado}
                onChange={(event) => cambiarFiltro("estado", event.target.value)}
                className={campoSelect}
                style={{ backgroundImage: chevron }}
              >
                <option value="">Todos</option>
                {opciones.estados.map((estado) => (
                  <option key={estado} value={estado}>
                    {estado}
                  </option>
                ))}
              </select>
            </Campo>

            <Campo label="Institución" id="institucion">
              <select
                id="institucion"
                value={filtros.institucion}
                onChange={(event) => cambiarFiltro("institucion", event.target.value)}
                className={campoSelect}
                style={{ backgroundImage: chevron }}
              >
                <option value="">Todas</option>
                {opciones.instituciones.map((institucion) => (
                  <option key={institucion} value={institucion}>
                    {institucion}
                  </option>
                ))}
              </select>
            </Campo>

            <Campo label="Tipo de beneficiario" id="beneficiario">
              <select
                id="beneficiario"
                value={filtros.beneficiario}
                onChange={(event) => cambiarFiltro("beneficiario", event.target.value)}
                className={campoSelect}
                style={{ backgroundImage: chevron }}
              >
                <option value="">Todos</option>
                {opciones.beneficiarios.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </Campo>

            <Campo label="Área temática o sector" id="tematica">
              <select
                id="tematica"
                value={filtros.tematica}
                onChange={(event) => cambiarFiltro("tematica", event.target.value)}
                className={campoSelect}
                style={{ backgroundImage: chevron }}
              >
                <option value="">Todas</option>
                {opciones.tematicas.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </Campo>

            <Campo label="Ubicación" id="alcance">
              <select
                id="alcance"
                value={filtros.alcance}
                onChange={(event) =>
                  setFiltros((actual) => ({
                    ...actual,
                    alcance: event.target.value as FiltrosConvocatoria["alcance"],
                    ubicacion: "",
                  }))
                }
                className={campoSelect}
                style={{ backgroundImage: chevron }}
              >
                <option value="">Todas</option>
                <option value="todo_uruguay">Todo Uruguay</option>
                <option value="departamento">Departamento</option>
                <option value="localidad">Localidad</option>
                <option value="region">Región</option>
              </select>
            </Campo>

            {filtros.alcance === "departamento" ? (
              <Campo label="Departamento" id="departamento">
                <select
                  id="departamento"
                  value={filtros.ubicacion}
                  onChange={(event) => cambiarFiltro("ubicacion", event.target.value)}
                  className={campoSelect}
                  style={{ backgroundImage: chevron }}
                >
                  <option value="">Elegí un departamento</option>
                  {opciones.departamentos.map((departamento) => (
                    <option key={departamento} value={departamento}>
                      {departamento}
                    </option>
                  ))}
                </select>
              </Campo>
            ) : null}

            {filtros.alcance === "region" ? (
              <Campo label="Región" id="region">
                <select
                  id="region"
                  value={filtros.ubicacion}
                  onChange={(event) => cambiarFiltro("ubicacion", event.target.value)}
                  className={campoSelect}
                  style={{ backgroundImage: chevron }}
                >
                  <option value="">Elegí una región</option>
                  {opciones.regiones.map((region) => (
                    <option key={region.id} value={region.id}>
                      {region.label}
                    </option>
                  ))}
                </select>
              </Campo>
            ) : null}

            {filtros.alcance === "localidad" ? (
              <Campo label="Localidad" id="localidad">
                <input
                  id="localidad"
                  value={filtros.ubicacion}
                  onChange={(event) => cambiarFiltro("ubicacion", event.target.value)}
                  placeholder="Por ejemplo, Punta del Este"
                  className="h-11 w-full rounded-xl border border-pine/20 bg-foam/70 px-4 text-sm text-ink outline-none transition focus:border-pine focus:bg-paper"
                />
              </Campo>
            ) : null}

            <Campo label="Monto mínimo" id="monto-min">
              <input
                id="monto-min"
                type="number"
                min={0}
                inputMode="numeric"
                value={filtros.montoMin}
                onChange={(event) => cambiarFiltro("montoMin", event.target.value)}
                placeholder="$U"
                className="h-11 w-full rounded-xl border border-pine/20 bg-foam/70 px-4 text-sm text-ink outline-none transition focus:border-pine focus:bg-paper"
              />
            </Campo>

            <Campo label="Monto máximo" id="monto-max">
              <input
                id="monto-max"
                type="number"
                min={0}
                inputMode="numeric"
                value={filtros.montoMax}
                onChange={(event) => cambiarFiltro("montoMax", event.target.value)}
                placeholder="$U"
                className="h-11 w-full rounded-xl border border-pine/20 bg-foam/70 px-4 text-sm text-ink outline-none transition focus:border-pine focus:bg-paper"
              />
            </Campo>

            <Campo label="Fechas y plazos" id="plazo">
              <select
                id="plazo"
                value={filtros.plazo}
                onChange={(event) =>
                  setFiltros((actual) => ({
                    ...actual,
                    plazo: event.target.value as FiltrosConvocatoria["plazo"],
                    fechaDesde: "",
                    fechaHasta: "",
                  }))
                }
                className={campoSelect}
                style={{ backgroundImage: chevron }}
              >
                <option value="">Sin filtrar por fecha</option>
                <option value="apertura">Por fecha de apertura</option>
                <option value="cierre">Por fecha de cierre</option>
                <option value="proximas">Próximas a abrir</option>
              </select>
            </Campo>

            {filtros.plazo === "apertura" || filtros.plazo === "cierre" ? (
              <>
                <Campo label="Desde" id="fecha-desde">
                  <input
                    id="fecha-desde"
                    type="date"
                    value={filtros.fechaDesde}
                    onChange={(event) => cambiarFiltro("fechaDesde", event.target.value)}
                    className="h-11 w-full rounded-xl border border-pine/20 bg-foam/70 px-4 text-sm text-ink outline-none transition focus:border-pine focus:bg-paper"
                  />
                </Campo>
                <Campo label="Hasta" id="fecha-hasta">
                  <input
                    id="fecha-hasta"
                    type="date"
                    value={filtros.fechaHasta}
                    onChange={(event) => cambiarFiltro("fechaHasta", event.target.value)}
                    className="h-11 w-full rounded-xl border border-pine/20 bg-foam/70 px-4 text-sm text-ink outline-none transition focus:border-pine focus:bg-paper"
                  />
                </Campo>
              </>
            ) : null}
          </div>
          {filtros.montoMin && filtros.montoMax && Number(filtros.montoMin) > Number(filtros.montoMax) ? (
            <p className="mt-3 text-sm text-clay" role="alert">
              El monto mínimo no puede ser mayor que el máximo.
            </p>
          ) : null}
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-ink/60">Estos filtros aplican a las convocatorias.</p>
            <button
              type="button"
              onClick={() => setFiltros(filtrosVacios)}
              className="text-sm text-pine-text transition hover:text-ink"
            >
              Limpiar filtros
            </button>
          </div>
        </div>
      </section>

      <section className="px-6 pb-20">
        <div
          className={`mx-auto grid max-w-6xl gap-6 ${mostrarResultados && mostrarPersonas ? "lg:grid-cols-[1.6fr_0.9fr]" : ""}`}
        >
          {error ? (
            <p className="rounded-2xl border border-clay/30 bg-paper px-5 py-4 text-sm text-ink lg:col-span-full" role="alert">
              {error} Comprobá que el backend esté disponible.
            </p>
          ) : null}
          {mostrarResultados && !error ? (
            <div className="flex flex-col gap-4">
              {cargando ? <Estado mensaje="Buscando en el repositorio..." /> : null}
              {!cargando && !error && visibles.length === 0 ? (
                <Estado mensaje="No hay convocatorias ni proyectos para esta búsqueda." />
              ) : null}
              {visibles.map((item, index) => {
                const clase = `rise rise-${(index % 4) + 1} block rounded-3xl border border-pine/10 bg-paper p-5 shadow-sm transition duration-300 sm:p-6 ${
                  item.href ? "hover:-translate-y-1 hover:border-pine/30 hover:shadow-lg" : ""
                }`;
                const contenido = (
                  <>
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <p className="text-xs font-medium tracking-[0.16em] text-clay uppercase">{item.tipo}</p>
                      <p className="text-xs text-pine-text">{item.detalle}</p>
                    </div>
                    <h2 className="font-display mt-2 text-2xl text-ink">{item.titulo}</h2>
                    <p className="mt-3 text-sm leading-relaxed text-ink/70">{item.descripcion}</p>
                    <p className="mt-4 text-sm text-ink/80">
                      <span className="text-pine-text">Estado</span> · {item.estado}
                    </p>
                    {item.financiamiento ? (
                      <p className="mt-2 text-sm text-ink/80">
                        <span className="text-pine-text">Financiamiento</span> · {item.financiamiento}
                      </p>
                    ) : null}
                  </>
                );
                return item.href ? (
                  <Link key={item.key} href={item.href} className={clase}>
                    {contenido}
                  </Link>
                ) : (
                  <article key={item.key} className={clase}>
                    {contenido}
                  </article>
                );
              })}
            </div>
          ) : null}

          {mostrarPersonas ? (
            <aside className="rise rise-2 h-fit rounded-[2rem] bg-pine-deep px-6 py-8 text-paper">
              <h2 className="font-display text-3xl">Investigación</h2>
              <p className="mt-2 text-sm leading-relaxed text-paper/75">
                Personas e instituciones con trayectoria en el tema.
              </p>

              {cargando ? <p className="mt-6 text-sm text-paper/75">Cargando investigadores...</p> : null}
              {!cargando && error ? (
                <p className="mt-6 text-sm text-paper/75">No se pudieron cargar los investigadores.</p>
              ) : null}
              {!cargando && !error && investigadores.length === 0 ? (
                <p className="mt-6 text-sm text-paper/75">No hay investigadores para esta búsqueda.</p>
              ) : null}

              <ul className="mt-6 flex flex-col gap-4">
                {investigadores.map((persona) => (
                  <li key={persona.id}>
                    <Link
                      href={`/repositorio/investigadores/${persona.id}`}
                      className="block rounded-2xl bg-white/10 p-4 ring-1 ring-white/15 transition duration-300 hover:bg-white/20"
                    >
                      <p className="font-display text-xl">{nombreCorto(persona)}</p>
                      <p className="mt-2 text-sm text-paper/80">{campo(persona.institucion, "Sin institución")}</p>
                      <p className="mt-1 text-sm text-paper/70">{campo(persona.titulo, "Sin título")}</p>
                      <p className="mt-3 text-xs tracking-wide text-gold uppercase">
                        Nivel · {campo(persona.nivel_sni, "—")}
                      </p>
                      <p className="mt-1 text-xs tracking-wide text-gold uppercase">
                        Categoría · {campo(persona.categoria_sni, "—")}
                      </p>
                      <p className="mt-3 text-sm leading-relaxed text-paper/75">
                        {campo(enunciado(persona.investigaciones), "Sin investigaciones cargadas")}
                      </p>
                    </Link>
                  </li>
                ))}
              </ul>
            </aside>
          ) : null}

          {!mostrarResultados && !mostrarPersonas ? (
            <Estado mensaje="Agregá un filtro para ver proyectos, convocatorias o investigadores." />
          ) : null}
        </div>
      </section>
    </main>
  );
}

function Campo({
  label,
  id,
  children,
}: {
  label: string;
  id: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm text-ink">
        {label}
      </label>
      {children}
    </div>
  );
}

function Estado({ mensaje }: { mensaje: string }) {
  return (
    <p className="rounded-3xl border border-dashed border-pine/30 bg-paper/70 px-6 py-10 text-center text-sm text-ink/70">
      {mensaje}
    </p>
  );
}

function Lupa() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <circle cx="7" cy="7" r="4.25" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M10.2 10.2 13 13" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
