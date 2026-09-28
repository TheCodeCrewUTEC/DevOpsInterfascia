// Devuelve una ruta interna segura a la que volver después del login.
// Evita que un ?callbackUrl= mande al usuario a otro sitio.
export function safeRedirect(url: string | null, origin: string): string {
  if (!url) {
    return "/";
  }

  try {
    const destino = new URL(url, origin);

    if (destino.origin !== origin) {
      return "/";
    }

    return `${destino.pathname}${destino.search}${destino.hash}`;
  } catch {
    return "/";
  }
}
