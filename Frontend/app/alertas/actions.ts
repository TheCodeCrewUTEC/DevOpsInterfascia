"use server";

import { revalidatePath } from "next/cache";
import { apiFetch } from "@/lib/api";
import { detalleRespuesta, validarDias, type Preferencias } from "@/lib/alertas";

export type EstadoFormulario = { ok: boolean; mensaje: string } | null;

function marcado(formData: FormData, campo: string) {
  return formData.get(campo) === "on";
}

export async function guardarPreferencias(
  _anterior: EstadoFormulario,
  formData: FormData,
): Promise<EstadoFormulario> {
  const dias = Number(String(formData.get("dias_anticipacion_cierre") ?? "").trim());
  const errorDias = validarDias(dias);
  if (errorDias) {
    return { ok: false, mensaje: errorDias };
  }

  const cuerpo: Omit<Preferencias, "email"> = {
    alerta_apertura: marcado(formData, "alerta_apertura"),
    alerta_cierre: marcado(formData, "alerta_cierre"),
    alerta_actualizacion: marcado(formData, "alerta_actualizacion"),
    dias_anticipacion_cierre: dias,
    email_habilitado: marcado(formData, "email_habilitado"),
  };

  // apiFetch manda el token de la sesión; sin sesión la API responde 401
  const response = await apiFetch("/api/alertas/preferencias", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cuerpo),
  });

  if (!response.ok) {
    return { ok: false, mensaje: await detalleRespuesta(response) };
  }

  revalidatePath("/alertas/preferencias");
  return { ok: true, mensaje: "Tus preferencias se guardaron." };
}
