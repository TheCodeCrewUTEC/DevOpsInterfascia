"use client";

import { useEffect, useState } from "react";
import Button from "./Button";
import { borrarSesion, leerUsuario } from "../lib/sesion";

type SesionMenuProps = {
  usuarioInicial: string | null;
};

export default function SesionMenu({ usuarioInicial }: SesionMenuProps) {
  const [usuario, setUsuario] = useState(usuarioInicial);

  useEffect(() => {
    function actualizar() {
      setUsuario(leerUsuario());
    }

    window.addEventListener("sesion-cambiada", actualizar);
    return () => window.removeEventListener("sesion-cambiada", actualizar);
  }, []);

  function cerrarSesion() {
    borrarSesion();
    window.location.assign("/");
  }

  if (!usuario) {
    return (
      <>
        <Button href="/login">Iniciar sesión</Button>
        <Button href="/registro" variant="secondary">
          Registrate
        </Button>
      </>
    );
  }

  return (
    <>
      <span className="max-w-40 truncate text-sm font-medium text-ink" title={usuario}>
        {usuario}
      </span>
      <Button variant="secondary" onClick={cerrarSesion}>
        Cerrar sesión
      </Button>
    </>
  );
}
