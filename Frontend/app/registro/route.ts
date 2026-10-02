import { signIn } from "@/auth";

// Keycloak abre el formulario de registro (prompt=create), no el de login.
// Al terminar, Auth.js vuelve a /registro/exitoso.
// No hay que llamar a /api/auth desde el servidor: detrás de Cloudflare
// el origen interno no es https://interfasciauy.com y esa llamada responde 500.
export async function GET() {
  await signIn(
    "keycloak",
    { redirectTo: "/registro/exitoso" },
    { prompt: "create" },
  );
}
