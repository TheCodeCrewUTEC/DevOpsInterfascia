import pytest

from app.services import deteccion_alertas_service, email_service

VARIABLES = ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM", "INTERFASCIA_APP_URL")


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch):
    for variable in VARIABLES:
        monkeypatch.delenv(variable, raising=False)


@pytest.fixture
def smtp_configurado(monkeypatch):
    monkeypatch.setenv("SMTP_USER", "cuenta@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "clave")


class SMTPFalso:
    """Reemplaza smtplib.SMTP / SMTP_SSL y registra lo que se le pide."""

    instancias = []

    def __init__(self, host, port, timeout=None, **kwargs):
        self.host, self.port, self.timeout = host, port, timeout
        self.llamadas = []
        self.mensajes = []
        SMTPFalso.instancias.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.llamadas.append("quit")

    def starttls(self, **kwargs):
        self.llamadas.append("starttls")

    def login(self, usuario, clave):
        self.llamadas.append(("login", usuario, clave))

    def send_message(self, mensaje):
        self.llamadas.append("send_message")
        self.mensajes.append(mensaje)


@pytest.fixture
def smtp_falso(monkeypatch):
    SMTPFalso.instancias = []
    monkeypatch.setattr(email_service.smtplib, "SMTP", SMTPFalso)
    monkeypatch.setattr(email_service.smtplib, "SMTP_SSL", SMTPFalso)
    return SMTPFalso


def test_configurado_sin_variables():
    assert email_service.configurado() is False


def test_configurado_con_usuario_y_clave(smtp_configurado):
    assert email_service.configurado() is True


def test_remitente_con_smtp_from_invalido_usa_smtp_user(monkeypatch, smtp_configurado):
    monkeypatch.setenv("SMTP_FROM", "Interfascia")
    assert email_service.remitente() == "cuenta@gmail.com"

    monkeypatch.setenv("SMTP_FROM", "avisos@interfascia.uy")
    assert email_service.remitente() == "avisos@interfascia.uy"


def test_enviar_correo_usa_starttls_y_login(smtp_configurado, smtp_falso):
    email_service.enviar_correo("ana@example.com", "Asunto", "Texto", "<p>Texto</p>")

    smtp = smtp_falso.instancias[0]
    assert (smtp.host, smtp.port, smtp.timeout) == ("smtp.gmail.com", 587, 15)
    assert smtp.llamadas == ["starttls", ("login", "cuenta@gmail.com", "clave"), "send_message", "quit"]

    mensaje = smtp.mensajes[0]
    assert mensaje["To"] == "ana@example.com"
    assert mensaje["Subject"] == "Asunto"
    assert "cuenta@gmail.com" in mensaje["From"]
    assert mensaje.get_body(("html",)).get_content().strip() == "<p>Texto</p>"


def test_enviar_correo_puerto_465_sin_starttls(monkeypatch, smtp_configurado, smtp_falso):
    monkeypatch.setenv("SMTP_PORT", "465")
    email_service.enviar_correo("ana@example.com", "Asunto", "Texto")

    assert "starttls" not in smtp_falso.instancias[0].llamadas
    assert "send_message" in smtp_falso.instancias[0].llamadas


def test_cuerpo_notificacion_escapa_html_y_arma_links(monkeypatch):
    monkeypatch.setenv("INTERFASCIA_APP_URL", "https://interfascia.uy/")
    asunto, texto, html = email_service.cuerpo_notificacion({
        "titulo": "Nueva convocatoria: <b>I+D</b>",
        "mensaje": "Línea 1\nCierre: 30/11/2026 & más",
        "convocatoria_id": 7,
    })

    assert asunto == "Interfascia: Nueva convocatoria: <b>I+D</b>"
    assert "https://interfascia.uy/repositorio/convocatorias/7" in texto
    assert "https://interfascia.uy/alertas" in texto
    assert "Mis alertas > Preferencias" in texto
    assert "<b>I+D</b>" not in html
    assert "&lt;b&gt;I+D&lt;/b&gt;" in html
    assert "Línea 1<br>Cierre: 30/11/2026 &amp; más" in html


def test_cuerpo_notificacion_sin_convocatoria():
    _, texto, html = email_service.cuerpo_notificacion({"titulo": "Hola", "mensaje": "x", "convocatoria_id": None})

    assert "repositorio" not in texto
    assert "http://localhost:3000/alertas" in html


def test_enviar_correos_pendientes_sin_smtp_no_toca_la_base(monkeypatch):
    def sin_base():
        raise AssertionError("no debería conectarse a la base")

    monkeypatch.setattr(deteccion_alertas_service, "get_connection", sin_base)

    assert deteccion_alertas_service.enviar_correos_pendientes() == {"omitido": "smtp no configurado"}
