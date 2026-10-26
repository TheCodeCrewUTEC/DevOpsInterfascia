import html as html_lib
import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

# Envío de correos de alertas (RF005-07). Usa las mismas variables SMTP_* que Keycloak
# para el código de verificación (ver keycloak/configurar-email-otp.sh).

PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PIE = "Podés desactivar estos correos en Mis alertas > Preferencias."


def configurado() -> bool:
    return bool(os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD"))


def remitente() -> str:
    # Igual que Keycloak: SMTP_FROM solo si es un correo válido; si no, la cuenta SMTP
    desde = (os.getenv("SMTP_FROM") or "").strip()
    return desde if PATRON_EMAIL.match(desde) else (os.getenv("SMTP_USER") or "").strip()


def url_app() -> str:
    return (os.getenv("INTERFASCIA_APP_URL") or "http://localhost:3000").rstrip("/")


def enviar_correo(destinatario: str, asunto: str, texto: str, html: str | None = None) -> None:
    host = os.getenv("SMTP_HOST") or "smtp.gmail.com"
    port = int(os.getenv("SMTP_PORT") or 587)

    mensaje = EmailMessage()
    mensaje["From"] = formataddr(("Interfascia", remitente()))
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto
    mensaje.set_content(texto)
    if html:
        mensaje.add_alternative(html, subtype="html")

    contexto = ssl.create_default_context()

    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=15, context=contexto) as smtp:
            smtp.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
            smtp.send_message(mensaje)
        return

    with smtplib.SMTP(host, port, timeout=15) as smtp:
        smtp.starttls(context=contexto)
        smtp.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
        smtp.send_message(mensaje)


def cuerpo_notificacion(notificacion: dict) -> tuple[str, str, str]:
    """Devuelve (asunto, texto plano, html) para una fila de notificacion."""

    titulo = notificacion.get("titulo") or "Nueva alerta"
    mensaje = notificacion.get("mensaje") or ""
    enlace_alertas = f"{url_app()}/alertas"
    convocatoria_id = notificacion.get("convocatoria_id")
    enlace_convocatoria = (
        f"{url_app()}/repositorio/convocatorias/{convocatoria_id}"
        if convocatoria_id is not None
        else None
    )

    asunto = f"Interfascia: {titulo}"

    texto = [titulo, "", mensaje, ""]
    if enlace_convocatoria:
        texto.append(f"Ver la convocatoria: {enlace_convocatoria}")
    texto += [f"Ver tus alertas: {enlace_alertas}", "", "--", PIE]

    e = html_lib.escape
    enlaces = []
    if enlace_convocatoria:
        enlaces.append(f'<a href="{e(enlace_convocatoria)}">Ver la convocatoria</a>')
    enlaces.append(f'<a href="{e(enlace_alertas)}">Ver tus alertas</a>')

    html = (
        '<div style="font-family: sans-serif; color: #1f2933;">'
        f"<h2>{e(titulo)}</h2>"
        f"<p>{'<br>'.join(e(linea) for linea in mensaje.splitlines())}</p>"
        f"<p>{' · '.join(enlaces)}</p>"
        f'<p style="font-size: 12px; color: #6b7280;">{e(PIE)}</p>'
        "</div>"
    )

    return asunto, "\n".join(texto), html
