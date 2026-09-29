"use server";

import { redirect } from "next/navigation";
import { auth, signOut } from "@/auth";
import { urlCierreKeycloak } from "@/lib/keycloak-logout";

// Cierra la sesión en la app y también en Keycloak
export async function cerrarSesion() {
  const session = await auth();

  await signOut({ redirect: false });

  redirect(urlCierreKeycloak(session?.idToken));
}
