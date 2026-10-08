"use client";

import { useEffect, useState } from "react";

// Cuenta regresiva y luego lleva al inicio (la cuenta aún no puede iniciar sesión).
export default function RedireccionInicio({ segundos }: { segundos: number }) {
  const [restantes, setRestantes] = useState(segundos);

  useEffect(() => {
    if (restantes <= 0) {
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.assign("/");
      return;
    }

    const timer = setTimeout(() => setRestantes((valor) => valor - 1), 1000);
    return () => clearTimeout(timer);
  }, [restantes]);

  return (
    <p className="mt-6 text-xs text-neutral-500" aria-live="polite">
      Te llevamos al inicio en {Math.max(restantes, 0)} segundos…
    </p>
  );
}
