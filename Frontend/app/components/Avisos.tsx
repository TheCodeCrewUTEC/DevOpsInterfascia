"use client";

import type { CSSProperties } from "react";
import { Toaster } from "sonner";

// Contenedor único de avisos efímeros (Sonner). Se monta una sola vez en el layout;
// desde cualquier componente de cliente: import { toast } from "sonner".
// Los avisos complementan los mensajes en pantalla (role="alert"), no los reemplazan.
// Sonner ya desactiva sus animaciones con prefers-reduced-motion.

const TEMA = {
  "--normal-bg": "var(--color-paper)",
  "--normal-text": "var(--color-ink)",
  "--normal-border": "var(--color-ink)",
  "--border-radius": "1rem",
} as CSSProperties;

export default function Avisos() {
  return (
    <Toaster
      position="bottom-right"
      closeButton
      visibleToasts={3}
      duration={4000}
      gap={10}
      containerAriaLabel="Avisos"
      style={TEMA}
      toastOptions={{
        closeButtonAriaLabel: "Cerrar aviso",
        classNames: {
          toast: "border-2! font-sans! text-sm! shadow-[0_8px_24px_-12px_rgb(16_42_60/0.35)]!",
          title: "font-medium!",
          description: "text-ink/70!",
          error: "border-clay! bg-[color-mix(in_srgb,var(--color-clay)_8%,var(--color-paper))]!",
          actionButton: "bg-ink! text-paper! rounded-full! px-3! font-medium!",
          closeButton: "border-ink/30! bg-paper! text-ink!",
        },
      }}
    />
  );
}
