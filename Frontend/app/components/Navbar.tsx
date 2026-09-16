import Link from "next/link";
import Button from "./Button";

export default function Navbar() {
  return (
    <nav className="relative flex items-center px-8 py-6">
      
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
      <div className="absolute left-1/2 flex -translate-x-1/2 items-center gap-10">
        <Link href="/repositorio">
          Repositorio
        </Link>

        <Link href="/">
          ¿Qué es Interfascia?
        </Link>

      </div>

      {/* Links */}
      <div className="absolute right-1 flex -translate-x-1/2 items-center gap-10 ">

        <Button>Iniciar sesión</Button>
      </div>

    </nav>
  );
}