"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { apiFetch } from "@/lib/api";

function volver(estado: string, mensaje: string, tipo: "ok" | "error") {
  const params = new URLSearchParams({ estado, mensaje, tipo });
  redirect(`/admin/usuarios?${params}`);
}

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

export async function sincronizarUsuarios(formData: FormData) {
  const estado = String(formData.get("estado_vista") ?? "todos");
  const response = await apiFetch("/api/admin/usuarios/sincronizar", { method: "POST" });

  revalidatePath("/admin/usuarios");

  if (!response.ok) {
    volver(estado, `No se pudo sincronizar: ${await detalleError(response)}`, "error");
  }

  const { sincronizados } = (await response.json()) as { sincronizados: number };
  volver(estado, `Se sincronizaron ${sincronizados} usuarios desde Keycloak.`, "ok");
}
