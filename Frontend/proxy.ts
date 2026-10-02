// Corre auth() en cada request para que la cookie de sesión se guarde con el token renovado
// (desde un Server Component como el Navbar no se pueden escribir cookies).
export { auth as proxy } from "@/auth";

export const config = {
  matcher: ["/((?!api/auth|_next/static|_next/image|favicon.ico|.*\\.(?:png|jpg|jpeg|svg|webp|ico)$).*)"],
};
