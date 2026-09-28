import Link from "next/link";
import Button from "./Button";
import { auth } from "@/auth";
import { cerrarSesion } from "../actions/auth";

export default async function Navbar() {
  const session = await auth();
  // Si no se pudo renovar el token, la sesión de Keycloak venció
  const logueado = Boolean(session?.user) && !session?.error;

  return (
    <nav className="sticky top-0 z-50 flex items-center bg-white px-8 py-6">

      {/* Logo + nombre */}
      <div className="flex items-center gap-6">
        <div className="bg-gray-300 px-4 py-1">
          Logo
        </div>

        <Link href="/">
          Interfascia
        </Link>
      </div>

      {/* Links */}
      <div className="absolute left-1/2 flex -translate-x-1/2 items-center gap-6 whitespace-nowrap">
        <Link href="/repositorio">
          Repositorio
        </Link>

        <Link href="/#que-es-interfascia">
          ¿Qué es Interfascia?
        </Link>

        <Link href="/consultor-ia">
          Consultor IA
        </Link>

        <Link href="/analisis-datos">
          Análisis de Datos
        </Link>
      </div>

      {/* Acciones */}
      <div className="ml-auto flex items-center gap-3">
        {logueado ? (
          <>
            <span>{session?.user?.name ?? session?.user?.email}</span>
            <form action={cerrarSesion}>
              <Button type="submit" variant="secondary">Cerrar sesión</Button>
            </form>
          </>
        ) : (
          <>
            {/* Sin prefetch: estas rutas redirigen a Keycloak */}
            <Button href="/login" prefetch={false}>Iniciar sesión</Button>
            <Button href="/registro" variant="secondary" prefetch={false}>Registrate</Button>
          </>
        )}
      </div>

    </nav>
  );
}
