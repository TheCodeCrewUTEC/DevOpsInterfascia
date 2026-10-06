import type { Metadata } from "next";
import Link from "next/link";
import { auth } from "@/auth";
import { apiFetch } from "@/lib/api";
import { esAdmin, idDeSesion } from "@/lib/roles";
import { sincronizarUsuarios } from "./actions";
import TablaUsuarios, { type Usuario } from "./TablaUsuarios";

export const metadata: Metadata = {
  title: "Gestión de usuarios | Interfascia",
};

export const dynamic = "force-dynamic";

const PESTANIAS = [
  { valor: "todos", label: "Todos" },
  { valor: "pendiente", label: "Pendientes" },
  { valor: "aprobado", label: "Habilitados" },
  { valor: "rechazado", label: "Deshabilitados" },
];

export default async function AdminUsuariosPage({
  searchParams,
}: {
  searchParams: Promise<{ estado?: string; mensaje?: string; tipo?: string }>;
}) {
  const params = await searchParams;
  const session = await auth();

  if (!esAdmin(session)) {
    return (
      <Encabezado titulo="Gestión de usuarios">
        <Aviso tipo="error" texto="Esta página es solo para administradores." />
      </Encabezado>
    );
  }

  const estado = PESTANIAS.some((p) => p.valor === params.estado) ? params.estado! : "todos";
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
    <Encabezado titulo="Gestión de usuarios">
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
          No hay usuarios en esta categoría.
        </p>
      ) : null}

      {usuarios.length > 0 ? (
        <TablaUsuarios usuarios={usuarios} miId={idDeSesion(session)} />
      ) : null}
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
          Las cuentas nuevas quedan deshabilitadas hasta que un administrador las habilite.
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
