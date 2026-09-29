import { signIn } from "@/auth";

// prompt=create hace que Keycloak abra directamente el formulario de registro.
// Al terminar, Keycloak deja la sesión iniciada; /registro/exitoso la cierra
// para que el usuario vea el aviso y entre con su email y contraseña.
export async function GET() {
  await signIn(
    "keycloak",
    { redirectTo: "/registro/exitoso" },
    { prompt: "create" },
  );
}
