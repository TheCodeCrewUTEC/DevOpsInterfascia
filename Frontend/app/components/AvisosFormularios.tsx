"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "/backend";
const CLAVE = "interfascia-formularios-estado";

type Formulario = {
  id: number;
  estado: string;
  nombre: string | null;
};

function leerEstados(): Record<string, string> {
  try {
    const valor = sessionStorage.getItem(CLAVE);
    if (!valor) return {};
    const datos = JSON.parse(valor) as unknown;
    if (!datos || typeof datos !== "object") return {};
    return datos as Record<string, string>;
  } catch {
    return {};
  }
}

export default function AvisosFormularios() {
  const [avisos, setAvisos] = useState<Formulario[]>([]);
  const pidioPermiso = useRef(false);

  useEffect(() => {
    let activo = true;
    let primera = sessionStorage.getItem(CLAVE) == null;

    async function consultar() {
      try {
        const response = await fetch(`${API_URL}/formularios/jobs`, {
          credentials: "include",
          cache: "no-store",
        });
        if (!response.ok || !activo) return;

        const lista = (await response.json()) as Formulario[];
        if (!activo) return;

        const anterior = leerEstados();
        const siguientes: Record<string, string> = {};
        const listos: Formulario[] = [];

        for (const item of lista) {
          const clave = String(item.id);
          siguientes[clave] = item.estado;
          const previo = anterior[clave];
          const veniaEnCurso = previo === "PENDING" || previo === "PROCESSING";
          if (!primera && veniaEnCurso && item.estado === "COMPLETED") {
            listos.push(item);
          }
        }

        sessionStorage.setItem(CLAVE, JSON.stringify(siguientes));
        primera = false;

        if (listos.length > 0) {
          setAvisos((actuales) => [...listos, ...actuales].slice(0, 4));
          if (typeof Notification !== "undefined" && Notification.permission === "granted") {
            for (const item of listos) {
              const aviso = new Notification("Tu formulario está listo", {
                body: item.nombre ?? "Ya podés revisarlo y generar el PDF.",
              });
              aviso.onclick = () => {
                window.focus();
                window.location.href = `/consultor-ia/mis-formularios/${item.id}`;
              };
            }
          }
        }

        const hayEnCurso = lista.some(
          (item) => item.estado === "PENDING" || item.estado === "PROCESSING",
        );
        if (
          hayEnCurso &&
          !pidioPermiso.current &&
          typeof Notification !== "undefined" &&
          Notification.permission === "default"
        ) {
          pidioPermiso.current = true;
          void Notification.requestPermission();
        }
      } catch {
        // El próximo ciclo vuelve a consultar.
      }
    }

    void consultar();
    const id = window.setInterval(() => void consultar(), 15000);
    return () => {
      activo = false;
      window.clearInterval(id);
    };
  }, []);

  if (avisos.length === 0) return null;

  return (
    <div className="fixed right-4 bottom-4 z-[60] flex w-[min(100%-2rem,22rem)] flex-col gap-2">
      {avisos.map((aviso) => (
        <div key={aviso.id} className="rounded-2xl border border-pine/20 bg-paper p-4 shadow-lg">
          <p className="text-sm font-medium text-ink">Tu formulario está listo</p>
          <p className="mt-1 text-sm text-ink/70">
            {aviso.nombre ?? "Ya podés revisarlo y generar el PDF."}
          </p>
          <div className="mt-3 flex gap-2">
            <Link
              href={`/consultor-ia/mis-formularios/${aviso.id}`}
              className="rounded-full bg-pine px-3 py-1.5 text-sm font-medium text-ink"
            >
              Ver formulario
            </Link>
            <button
              type="button"
              onClick={() => setAvisos((actuales) => actuales.filter((item) => item.id !== aviso.id))}
              className="rounded-full px-3 py-1.5 text-sm text-ink/70 transition hover:bg-foam hover:text-ink"
            >
              Cerrar
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
