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

async function revisar(formData: FormData, accion: "aprobar" | "rechazar") {
  const keycloakId = String(formData.get("keycloak_id") ?? "");
  const nombre = String(formData.get("nombre") ?? "el usuario");
  const estado = String(formData.get("estado_vista") ?? "pendiente");

  const response = await apiFetch(
    `/api/admin/usuarios/${encodeURIComponent(keycloakId)}/${accion}`,
    { method: "POST" },
  );

  revalidatePath("/admin/usuarios");

  if (!response.ok) {
    volver(estado, `No se pudo ${accion} a ${nombre}: ${await detalleError(response)}`, "error");
  }

  volver(
    estado,
    accion === "aprobar"
      ? `${nombre} fue aprobado/a y ya puede iniciar sesión.`
      : `${nombre} fue rechazado/a.`,
    "ok",
  );
}

export async function aprobarUsuario(formData: FormData) {
  await revisar(formData, "aprobar");
}

export async function rechazarUsuario(formData: FormData) {
  await revisar(formData, "rechazar");
}

export async function sincronizarUsuarios(formData: FormData) {
  const estado = String(formData.get("estado_vista") ?? "pendiente");
  const response = await apiFetch("/api/admin/usuarios/sincronizar", { method: "POST" });

  revalidatePath("/admin/usuarios");

  if (!response.ok) {
    volver(estado, `No se pudo sincronizar: ${await detalleError(response)}`, "error");
  }

  const { sincronizados } = (await response.json()) as { sincronizados: number };
  volver(estado, `Se sincronizaron ${sincronizados} usuarios desde Keycloak.`, "ok");
}
