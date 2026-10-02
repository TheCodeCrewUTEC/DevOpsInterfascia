const COOKIE = "sesion";

export function leerUsuario() {
  const entrada = document.cookie
    .split("; ")
    .find((parte) => parte.startsWith(`${COOKIE}=`));

  if (!entrada) return null;

  const valor = entrada.slice(COOKIE.length + 1);
  if (!valor) return null;

  try {
    return decodeURIComponent(valor);
  } catch {
    return valor;
  }
}

export function guardarSesion(usuario: string) {
  document.cookie = `${COOKIE}=${encodeURIComponent(usuario)}; Path=/; Max-Age=${60 * 60 * 24 * 7}; SameSite=Lax`;
  window.dispatchEvent(new Event("sesion-cambiada"));
}

export function borrarSesion() {
  document.cookie = `${COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
  window.dispatchEvent(new Event("sesion-cambiada"));
}
