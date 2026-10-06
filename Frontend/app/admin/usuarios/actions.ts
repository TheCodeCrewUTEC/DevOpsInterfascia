"use server";

import { revalidatePath } from "next/cache";
import { apiFetch } from "@/lib/api";

async function detalleError(response: Response) {
  try {
    const datos = (await response.json()) as { detail?: string };
    return datos.detail ?? `Error ${response.status}`;
  } catch {
    return `Error ${response.status}`;
  }
}

export type Resultado = { ok: boolean; mensaje: string };

export async function cambiarHabilitado(
  keycloakId: string,
  nombre: string,
  habilitado: boolean,
): Promise<Resultado> {
  // Habilitar = aprobar la cuenta; deshabilitar = rechazarla (Keycloak la marca enabled=false)
  const accion = habilitado ? "aprobar" : "rechazar";
  const response = await apiFetch(
    `/api/admin/usuarios/${encodeURIComponent(keycloakId)}/${accion}`,
    { method: "POST" },
  );

  revalidatePath("/admin/usuarios");

  if (!response.ok) {
    return { ok: false, mensaje: `No se pudo actualizar a ${nombre}: ${await detalleError(response)}` };
  }

  return {
    ok: true,
    mensaje: habilitado
      ? `${nombre} fue habilitado/a y ya puede iniciar sesión.`
      : `${nombre} fue deshabilitado/a.`,
  };
}

export async function cambiarRol(
  keycloakId: string,
  nombre: string,
  rol: string,
): Promise<Resultado> {
  const response = await apiFetch(`/api/admin/usuarios/${encodeURIComponent(keycloakId)}/rol`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rol: rol || null }),
  });

  revalidatePath("/admin/usuarios");

  if (!response.ok) {
    return { ok: false, mensaje: `No se pudo cambiar el rol de ${nombre}: ${await detalleError(response)}` };
  }

  return { ok: true, mensaje: `Se actualizó el rol de ${nombre}.` };
}
