import { auth } from "@/auth";

export const proxy = auth;

export const config = {
  matcher: [
    "/((?!api/auth|backend|_next/static|_next/image|favicon.ico|.*\\.(?:png|jpg|jpeg|svg|webp|ico)$).*)",
  ],
};