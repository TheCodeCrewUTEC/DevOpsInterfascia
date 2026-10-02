import { redirect } from "next/navigation";
import { auth, signOut } from "@/auth";
import { urlCierreKeycloak } from "@/lib/keycloak-logout";

// Se llega acá justo después de registrarse. Keycloak ya inició la sesión,
// pero el registro no debe dejar al usuario adentro: cerramos la sesión en la
// app y en Keycloak, y mostramos el aviso de registro exitoso.
export async function GET() {
  const session = await auth();

  if (!session) {
    redirect("/");
  }

  await signOut({ redirect: false });

  redirect(urlCierreKeycloak(session.idToken, "/registro/confirmado"));
}
