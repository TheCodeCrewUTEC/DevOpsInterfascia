import type { Metadata } from "next";
import Link from "next/link";
import { auth } from "@/auth";
import { apiFetch } from "@/lib/api";
import { esAdmin } from "@/lib/roles";
import { aprobarUsuario, rechazarUsuario, sincronizarUsuarios } from "./actions";

export const metadata: Metadata = {
  title: "Usuarios | Interfascia",
};

export const dynamic = "force-dynamic";

type Usuario = {
  keycloak_id: string;
  email: string | null;
  nombre: string | null;
  apellido: string | null;
  celular: string | null;
  departamento_residencia: string | null;
  departamentos_actuacion: string[];
  instituciones: string[];
  perfil: string | null;
  perfil_otro: string | null;
  rol: string | null;
  estado: "pendiente" | "aprobado" | "rechazado";
  revisado_por: string | null;
  revisado_en: string | null;
  creado: string;
};

const PESTANIAS = [
  { valor: "pendiente", label: "Pendientes" },
  { valor: "aprobado", label: "Aprobados" },
  { valor: "rechazado", label: "Rechazados" },
  { valor: "todos", label: "Todos" },
];

const ESTILO_ESTADO: Record<Usuario["estado"], string> = {
  pendiente: "bg-gold/30 text-ink",
  aprobado: "bg-foam text-pine-text",
  rechazado: "bg-clay/15 text-clay",
};

const NOMBRE_ROL: Record<string, string> = {
  admin: "Administrador",
  gestor_innovacion: "Gestor/a de innovación",
  investigador: "Investigador/a",
  emprendedor: "Emprendedor/a / Empresario/a",
};

function formatFecha(valor: string | null) {
  if (!valor) return "—";
  return new Intl.DateTimeFormat("es-UY", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "America/Montevideo",
  }).format(new Date(valor));
}

function nombreCompleto(usuario: Usuario) {
  const nombre = [usuario.nombre, usuario.apellido].filter(Boolean).join(" ");
  return nombre || usuario.email || "Sin nombre";
}

function perfilElegido(usuario: Usuario) {
  if (usuario.perfil === "Otros" && usuario.perfil_otro) {
    return `Otros: ${usuario.perfil_otro}`;
  }
  return usuario.perfil ?? "Sin perfil";
}

export default async function AdminUsuariosPage({
  searchParams,
}: {
  searchParams: Promise<{ estado?: string; mensaje?: string; tipo?: string }>;
}) {
  const params = await searchParams;
  const session = await auth();

  if (!esAdmin(session)) {
    return (
      <Encabezado titulo="Usuarios">
        <Aviso tipo="error" texto="Esta página es solo para administradores." />
      </Encabezado>
    );
  }

  const estado = PESTANIAS.some((p) => p.valor === params.estado) ? params.estado! : "pendiente";
  const filtro = estado === "todos" ? "" : `?estado=${estado}`;

  let usuarios: Usuario[] = [];
  let error: string | null = null;

  try {
    const response = await apiFetch(`/api/admin/usuarios${filtro}`, { cache: "no-store" });
    if (response.ok) {
      usuarios = (await response.json()) as Usuario[];
    } else {
      error = `No se pudieron cargar los usuarios (${response.status}).`;
    }
  } catch {
    error = "No se pudo conectar con la API.";
  }

  return (
    <Encabezado titulo="Usuarios">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <nav className="flex flex-wrap gap-2" aria-label="Filtrar por estado">
          {PESTANIAS.map((pestania) => (
            <Link
              key={pestania.valor}
              href={`/admin/usuarios?estado=${pestania.valor}`}
              aria-current={pestania.valor === estado ? "page" : undefined}
              className={
                pestania.valor === estado
                  ? "rounded-full bg-pine px-4 py-2 text-sm font-medium text-ink"
                  : "rounded-full border border-pine/30 bg-paper px-4 py-2 text-sm text-ink transition hover:border-pine hover:bg-foam"
              }
            >
              {pestania.label}
            </Link>
          ))}
        </nav>

        <form action={sincronizarUsuarios}>
          <input type="hidden" name="estado_vista" value={estado} />
          <button
            type="submit"
            title="Copia a la base los usuarios de Keycloak (por ejemplo, registros anteriores a esta página)"
            className="rounded-full border border-pine/40 bg-paper px-4 py-2 text-sm text-ink transition hover:border-pine hover:bg-foam"
          >
            Sincronizar con Keycloak
          </button>
        </form>
      </div>

      {params.mensaje ? (
        <Aviso tipo={params.tipo === "error" ? "error" : "ok"} texto={params.mensaje} />
      ) : null}

      {error ? <Aviso tipo="error" texto={error} /> : null}

      {!error && usuarios.length === 0 ? (
        <p className="rounded-3xl border border-pine/10 bg-paper p-6 text-sm text-ink/70">
          {estado === "pendiente"
            ? "No hay registros pendientes de aprobación."
            : "No hay usuarios en esta categoría."}
        </p>
      ) : null}

      <div className="flex flex-col gap-4">
        {usuarios.map((usuario) => (
          <article
            key={usuario.keycloak_id}
            className="rounded-3xl border border-pine/10 bg-paper p-5 shadow-sm sm:p-6"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="text-lg font-medium text-ink">{nombreCompleto(usuario)}</h2>
                <p className="break-all text-sm text-ink/70">{usuario.email}</p>
              </div>
              <span
                className={`rounded-full px-3 py-1 text-xs font-medium capitalize ${ESTILO_ESTADO[usuario.estado]}`}
              >
                {usuario.estado}
              </span>
            </div>

            <dl className="mt-4 grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
              <Dato titulo="Perfil elegido" valor={perfilElegido(usuario)} />
              <Dato
                titulo="Rol asignado"
                valor={usuario.rol ? NOMBRE_ROL[usuario.rol] ?? usuario.rol : "Sin rol"}
              />
              <Dato titulo="Celular" valor={usuario.celular} />
              <Dato titulo="Departamento de residencia" valor={usuario.departamento_residencia} />
              <Dato titulo="Departamentos de actuación" valor={usuario.departamentos_actuacion.join(", ")} />
              <Dato titulo="Instituciones" valor={usuario.instituciones.join(", ")} />
              <Dato titulo="Registrado" valor={formatFecha(usuario.creado)} />
              {usuario.revisado_por ? (
                <Dato
                  titulo="Revisado"
                  valor={`${usuario.revisado_por} · ${formatFecha(usuario.revisado_en)}`}
                />
              ) : null}
            </dl>

            <div className="mt-5 flex flex-wrap justify-end gap-2">
              {usuario.estado !== "rechazado" ? (
                <form action={rechazarUsuario}>
                  <CamposOcultos usuario={usuario} estadoVista={estado} />
                  <button
                    type="submit"
                    className="rounded-full border border-clay/50 bg-paper px-4 py-2 text-sm text-clay transition hover:bg-clay/10"
                  >
                    {usuario.estado === "aprobado" ? "Deshabilitar" : "Rechazar"}
                  </button>
                </form>
              ) : null}
              {usuario.estado !== "aprobado" ? (
                <form action={aprobarUsuario}>
                  <CamposOcultos usuario={usuario} estadoVista={estado} />
                  <button
                    type="submit"
                    className="rounded-full bg-pine px-4 py-2 text-sm font-medium text-ink shadow-sm transition hover:bg-pine-hover"
                  >
                    Aprobar
                  </button>
                </form>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </Encabezado>
  );
}

function Encabezado({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-6 py-10">
      <div>
        <p className="text-sm font-medium tracking-[0.18em] text-clay uppercase">Administración</p>
        <h1 className="font-display mt-2 text-4xl text-ink">{titulo}</h1>
        <p className="mt-2 text-sm text-ink/70">
          Las cuentas nuevas quedan pendientes hasta que un administrador las apruebe.
        </p>
      </div>
      {children}
    </main>
  );
}

function Aviso({ tipo, texto }: { tipo: "ok" | "error"; texto: string }) {
  return (
    <p
      role={tipo === "error" ? "alert" : "status"}
      className={
        tipo === "error"
          ? "rounded-2xl border border-clay/30 bg-clay/10 px-4 py-3 text-sm text-ink"
          : "rounded-2xl border border-pine/30 bg-foam px-4 py-3 text-sm text-ink"
      }
    >
      {texto}
    </p>
  );
}

function Dato({ titulo, valor }: { titulo: string; valor: string | null | undefined }) {
  return (
    <div>
      <dt className="text-xs font-medium tracking-[0.12em] text-ink/50 uppercase">{titulo}</dt>
      <dd className="mt-1 text-ink">{valor?.trim() ? valor : "—"}</dd>
    </div>
  );
}

function CamposOcultos({ usuario, estadoVista }: { usuario: Usuario; estadoVista: string }) {
  return (
    <>
      <input type="hidden" name="keycloak_id" value={usuario.keycloak_id} />
      <input type="hidden" name="nombre" value={nombreCompleto(usuario)} />
      <input type="hidden" name="estado_vista" value={estadoVista} />
    </>
  );
}
