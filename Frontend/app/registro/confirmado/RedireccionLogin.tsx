"use client";

import { useEffect, useState } from "react";

// Cuenta regresiva y luego lleva al inicio de sesión
export default function RedireccionLogin({ segundos }: { segundos: number }) {
  const [restantes, setRestantes] = useState(segundos);

  useEffect(() => {
    if (restantes <= 0) {
      // Navegación completa a propósito: /login es un route handler que redirige a
      // Keycloak, y el router de Next no puede seguir esa redirección a otro dominio.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.assign("/login");
      return;
    }

    const timer = setTimeout(() => setRestantes((valor) => valor - 1), 1000);
    return () => clearTimeout(timer);
  }, [restantes]);

  return (
    <p className="mt-6 text-xs text-neutral-500" aria-live="polite">
      Te llevamos al inicio de sesión en {Math.max(restantes, 0)} segundos…
    </p>
  );
}
