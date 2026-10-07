"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { auth, signOut } from "@/auth";
import { apiFetch } from "@/lib/api";
import { urlCierreKeycloak } from "@/lib/keycloak-logout";

export type EstadoFormulario = { ok: boolean; mensaje: string } | null;

async function detalleError(response: Response) {
  try {
    const datos = (await response.json()) as { detail?: unknown };
    return typeof datos.detail === "string" ? datos.detail : `Error ${response.status}`;
  } catch {
    return `Error ${response.status}`;
  }
}

function texto(formData: FormData, campo: string) {
  return String(formData.get(campo) ?? "").trim();
}

function lista(formData: FormData, campo: string) {
  return formData.getAll(campo).map(String).filter(Boolean);
}

export async function guardarPerfil(
  _anterior: EstadoFormulario,
  formData: FormData,
): Promise<EstadoFormulario> {
  const response = await apiFetch("/api/perfil", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      nombre: texto(formData, "nombre"),
      apellido: texto(formData, "apellido"),
      celular: texto(formData, "celular") || null,
      departamento_residencia: texto(formData, "departamento_residencia"),
      departamentos_actuacion: lista(formData, "departamentos_actuacion"),
      instituciones: lista(formData, "instituciones"),
      perfil_otro: texto(formData, "perfil_otro") || null,
    }),
  });

  if (!response.ok) {
    return { ok: false, mensaje: await detalleError(response) };
  }

  revalidatePath("/perfil");
  return { ok: true, mensaje: "Tus datos se guardaron." };
}

export async function cambiarContrasena(
  _anterior: EstadoFormulario,
  formData: FormData,
): Promise<EstadoFormulario> {
  const actual = String(formData.get("actual") ?? "");
  const nueva = String(formData.get("nueva") ?? "");

  if (nueva !== String(formData.get("confirmacion") ?? "")) {
    return { ok: false, mensaje: "La confirmación no coincide con la contraseña nueva." };
  }

  const response = await apiFetch("/api/perfil/contrasena", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ actual, nueva }),
  });

  if (!response.ok) {
    return { ok: false, mensaje: await detalleError(response) };
  }

  // La API ya cerró las sesiones en Keycloak; se cierra la de la app y se vuelve al login
  const session = await auth();
  await signOut({ redirect: false });
  redirect(urlCierreKeycloak(session?.idToken, "/login"));
}
