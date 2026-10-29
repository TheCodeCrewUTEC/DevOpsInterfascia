"use client";

import type { ReactNode } from "react";
import { Drawer } from "vaul";

// Panel que sube desde abajo (Vaul) para mobile: mismo patrón que una hoja nativa.
// Trae foco atrapado, cierre con Esc / tocando afuera / arrastrando el handle, y título accesible.

interface PanelInferiorProps {
  abierto: boolean;
  onAbiertoChange: (abierto: boolean) => void;
  titulo: string;
  descripcion?: string;
  // Botón que abre el panel (se renderiza tal cual, va dentro de Drawer.Trigger)
  disparador: ReactNode;
  children: ReactNode;
}

export default function PanelInferior({
  abierto,
  onAbiertoChange,
  titulo,
  descripcion,
  disparador,
  children,
}: PanelInferiorProps) {
  return (
    <Drawer.Root open={abierto} onOpenChange={onAbiertoChange} repositionInputs={false}>
      <Drawer.Trigger asChild>{disparador}</Drawer.Trigger>
      <Drawer.Portal>
        <Drawer.Overlay className="fixed inset-0 z-50 bg-ink/40" />
        <Drawer.Content
          className="fixed inset-x-0 bottom-0 z-50 flex max-h-[88dvh] flex-col rounded-t-3xl border-2 border-b-0 border-ink bg-paper outline-none"
          style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
        >
          <Drawer.Handle className="mt-3 mb-1 bg-ink/25!" />
          <div className="px-5 pt-2 pb-3">
            <Drawer.Title className="font-display text-xl text-ink">{titulo}</Drawer.Title>
            {descripcion ? (
              <Drawer.Description className="mt-1 text-sm text-ink/70">{descripcion}</Drawer.Description>
            ) : (
              <Drawer.Description className="sr-only">{titulo}</Drawer.Description>
            )}
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 pb-5">{children}</div>
        </Drawer.Content>
      </Drawer.Portal>
    </Drawer.Root>
  );
}
