"""Entra al portal de beneficiarios de ANDE y abre cada formulario.

Si después de Postular (o de abrir una postulación ya empezada) aparece el
botón Continuar, escribe "Prueba" en el título y lo aprieta. Si esa pantalla
no está, lee los campos del formulario directo. No aprieta Finalizar ni
Guardar para más tarde. Al terminar borra cada postulación que quedó En proceso.

Credenciales en Backend/.env (ese archivo no se sube a git):

    ANDE_EMAIL=tu-correo
    ANDE_PASSWORD=tu-clave

Desde Backend/, con el venv activo:

    pip install playwright
    playwright install chromium
    python worker/scraping/portal_ande.py

ANDE_HEADFUL=1 abre el navegador para ver qué hace.
El JSON queda en worker/scraping/salida/formularios_ande.json.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

LOGIN_URL = "https://portal.ande.org.uy/login"
INICIO_URL = "https://portal.ande.org.uy/start"
NOMBRE_PROYECTO = "Prueba"
SALIDA = Path(__file__).resolve().parent / "salida" / "formularios_ande.json"


def _credenciales():
    email = os.environ.get("ANDE_EMAIL", "").strip()
    password = os.environ.get("ANDE_PASSWORD", "")
    if not email or not password:
        sys.exit(
            "Definí ANDE_EMAIL y ANDE_PASSWORD en Backend/.env. "
            "No las escribas en el código."
        )
    return email, password


def _error_login(page):
    caja = page.locator("[id='extFrmId:errorMsgPGId']")
    if caja.count() == 0:
        return ""
    return " ".join(caja.inner_text(timeout=1000).split())


def _login(page, email, password):
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    page.locator("[id='extFrmId:loginId']").fill(email)
    page.locator("[id='extFrmId:passId']").fill(password)
    page.locator("[id='extFrmId:andeSBid']").click()
    try:
        page.wait_for_function(
            """() => {
                const error = document.querySelector("[id='extFrmId:errorMsgPGId']");
                if (error && error.textContent.trim()) return true;
                const pass = document.querySelector("[id='extFrmId:passId']");
                return !pass || !location.pathname.endsWith('/login');
            }""",
            timeout=25000,
        )
    except PlaywrightTimeout:
        _fallo(page, "El portal no respondió al login.")
    mensaje = _error_login(page)
    if mensaje or page.locator("[id='extFrmId:passId']").count():
        _fallo(page, mensaje or "La sesión no entró: sigue en el login.")


def _fallo(page, motivo):
    ruta = Path(tempfile.gettempdir()) / "ande-portal-login.png"
    try:
        page.screenshot(path=str(ruta), full_page=True)
    except Exception:
        ruta = None
    extra = f" Captura: {ruta}" if ruta else ""
    sys.exit(f"{motivo}{extra}")


def _convocatorias(page):
    page.wait_for_selector("a.btn-open-call", timeout=20000)
    return page.locator("a.btn-open-call").evaluate_all(
        """(botones) => botones.map((boton) => {
            const fila = boton.closest("tr");
            const referencia = fila ? fila.querySelector("td:nth-child(2)") : null;
            return (referencia ? referencia.innerText : "").replace(/\\s+/g, " ").trim();
        }).filter(Boolean)"""
    )


def _volver(page):
    try:
        page.goto(INICIO_URL, wait_until="commit", timeout=20000)
    except Exception:
        pass
    page.wait_for_selector("a.btn-open-call", timeout=20000)


def _esperar_entrada(page):
    page.wait_for_function(
        """() => {
            const continuar = document.querySelector("[id='aPLfRMid:ApFCtpsID']");
            const frame = document.querySelector("#idCurrentFrame");
            const visible = (el) => el && el.getBoundingClientRect().height > 0;
            return visible(continuar) || visible(frame);
        }""",
        timeout=20000,
    )


def _entrar_al_formulario(page):
    _esperar_entrada(page)
    escribio = False
    continuar = page.locator("[id='aPLfRMid:ApFCtpsID']")
    if continuar.count() and continuar.first.is_visible():
        campo = page.locator("[id='aPLfRMid:itTPR']")
        if campo.count() and campo.first.is_visible():
            campo.fill(NOMBRE_PROYECTO)
            escribio = True
        continuar.first.click()
    frame = _frame_formulario(page)
    formulario = _leer_formulario(frame)
    formulario["titulo_escrito"] = NOMBRE_PROYECTO if escribio else ""
    return formulario


def _frame_formulario(page):
    page.wait_for_selector("#idCurrentFrame", timeout=25000)
    for _ in range(20):
        frame = next((item for item in page.frames if "fo.ande.org.uy" in item.url), None)
        if frame is not None:
            try:
                frame.wait_for_selector("label, h1, h2, h3", timeout=3000)
                return frame
            except PlaywrightTimeout:
                pass
        page.wait_for_timeout(500)
    raise PlaywrightTimeout("El formulario no cargó dentro del iframe.")


def _leer_formulario(frame):
    return frame.evaluate(
        """() => {
            const limpio = (texto) => (texto || "").replace(/\\s+/g, " ").trim();
            const etiquetaDe = (el) => {
                const porId = el.id
                    ? document.querySelector(`label[for="${CSS.escape(el.id)}"]`)
                    : null;
                if (porId) return limpio(porId.innerText);
                const sufijo = el.id && el.id.includes("·") ? el.id.split("·").pop() : "";
                const porSufijo = sufijo
                    ? document.querySelector(`label[for="${CSS.escape(sufijo)}"]`)
                    : null;
                if (porSufijo) return limpio(porSufijo.innerText);
                const alLado = el.parentElement && el.parentElement.querySelector("span");
                if (alLado && (el.type === "checkbox" || el.type === "radio")) {
                    return limpio(alLado.innerText);
                }
                return limpio(el.getAttribute("placeholder") || el.name || el.id);
            };
            const tipoDe = (el) => {
                if (el.tagName === "TEXTAREA") return "textarea";
                if (el.tagName === "SELECT") return "select";
                if (el.type === "select-one" || el.type === "select-multiple") return "select";
                return el.type || "text";
            };
            const secciones = [];
            const campos = [];
            let seccion = "General";
            for (const el of document.querySelectorAll("h1, h2, h3, h4, legend, input, textarea, select")) {
                if (/^H[1-4]$/.test(el.tagName) || el.tagName === "LEGEND") {
                    const titulo = limpio(el.innerText);
                    if (!titulo) continue;
                    seccion = titulo;
                    secciones.push(titulo);
                    continue;
                }
                if (el.type === "hidden" || el.type === "submit" || el.type === "button") continue;
                const etiqueta = etiquetaDe(el).slice(0, 400);
                const selector = el.id || el.name || "";
                if (!etiqueta || etiqueta === "*" || !selector) continue;
                const opciones = el.tagName === "SELECT"
                    ? [...el.options]
                        .map((opcion) => limpio(opcion.text))
                        .filter((texto) => texto && !texto.startsWith("--"))
                        .slice(0, 300)
                    : [];
                campos.push({
                    seccion,
                    etiqueta,
                    tipo: tipoDe(el),
                    requerido: Boolean(el.required || etiqueta.endsWith("*")),
                    opciones,
                    selector,
                });
            }
            const acciones = [...document.querySelectorAll("button, input[type='submit'], input[type='button']")]
                .map((el) => limpio(el.innerText || el.value))
                .filter(Boolean);
            return { secciones, campos, acciones };
        }"""
    )


def _postulaciones(page):
    return page.evaluate(
        """() => {
            const limpio = (texto) => (texto || "").replace(/\\s+/g, " ").trim();
            return [...document.querySelectorAll('a[title="Editar postulación"]')]
                .filter((el) => !el.id.includes("Mb"))
                .map((el) => {
                    const fila = el.closest("tr");
                    const texto = limpio(fila && fila.innerText);
                    return { id: el.id, nombre: texto.split("(P)")[0].trim() };
                })
                .filter((item) => item.nombre);
        }"""
    )


def _abrir(page, referencia):
    fila = page.locator("tr:has(a.btn-open-call)", has_text=referencia)
    if fila.count() == 0:
        return {"error": "El link Postular ya no está en la lista."}
    fila.first.locator("a.btn-open-call").click()
    page.wait_for_url("**/c/**", timeout=20000)
    return _entrar_al_formulario(page)


def _abrir_postulacion(page, boton_id):
    page.evaluate("(id) => document.getElementById(id).click()", boton_id)
    page.wait_for_url(lambda url: "/c/" in url or "/s/" in url, timeout=20000)
    return _entrar_al_formulario(page)


def _borrar_en_proceso(page):
    _volver(page)
    borradas = []
    while True:
        pendiente = page.evaluate(
            """() => {
                const limpio = (texto) => (texto || "").replace(/\\s+/g, " ").trim();
                const boton = [...document.querySelectorAll('a[title="Borrar postulación"]')]
                    .find((el) => {
                        const fila = el.closest("tr");
                        return !el.id.includes("Mb")
                            && limpio(fila && fila.innerText).includes("En proceso");
                    });
                if (!boton) return null;
                return {
                    id: boton.id,
                    texto: limpio(boton.closest("tr").innerText),
                };
            }"""
        )
        if not pendiente:
            break
        page.evaluate("(id) => document.getElementById(id).click()", pendiente["id"])
        page.wait_for_function(
            """() => document.querySelector("#modalDeleteSubmission")
                ?.classList.contains("show")""",
            timeout=10000,
        )
        page.locator("[id='modalDeleteSubmissionForm:mdsYBtn']").click()
        # Al rearmar la tabla, JSF reutiliza el mismo id en la fila siguiente.
        try:
            page.wait_for_function(
                """(texto) => {
                    const limpio = (valor) => (valor || "").replace(/\\s+/g, " ").trim();
                    const modal = document.querySelector("#modalDeleteSubmission");
                    const filas = [...document.querySelectorAll('a[title="Borrar postulación"]')]
                        .filter((el) => !el.id.includes("Mb"))
                        .map((el) => limpio(el.closest("tr") && el.closest("tr").innerText));
                    const cerrada = !modal || !modal.classList.contains("show");
                    return cerrada && !filas.includes(texto);
                }""",
                arg=pendiente["texto"],
                timeout=15000,
            )
        except PlaywrightTimeout:
            _volver(page)
            sigue = page.evaluate(
                """(texto) => {
                    const limpio = (valor) => (valor || "").replace(/\\s+/g, " ").trim();
                    return [...document.querySelectorAll('a[title="Borrar postulación"]')]
                        .filter((el) => !el.id.includes("Mb"))
                        .some((el) => limpio(el.closest("tr") && el.closest("tr").innerText) === texto);
                }""",
                pendiente["texto"],
            )
            if sigue:
                raise
        borradas.append(pendiente["texto"])
        print(f"borrada {pendiente['texto']}", flush=True)
    return borradas


def _cargar():
    if not SALIDA.exists():
        return []
    return json.loads(SALIDA.read_text(encoding="utf-8")).get("formularios", [])


def _guardar(formularios):
    SALIDA.parent.mkdir(exist_ok=True)
    SALIDA.write_text(
        json.dumps({"formularios": formularios}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main():
    email, password = _credenciales()
    headless = os.environ.get("ANDE_HEADFUL", "") != "1"
    formularios = _cargar()
    ya = {item["convocatoria"] for item in formularios}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context(locale="es-UY", viewport={"width": 1400, "height": 1200})
        page = context.new_page()
        _login(page, email, password)
        referencias = _convocatorias(page)
        pendientes = [
            item for item in _postulaciones(page)
            if item["nombre"] not in ya and item["nombre"] not in referencias
        ]
        for indice, referencia in enumerate(referencias):
            if indice:
                _volver(page)
            try:
                formulario = _abrir(page, referencia)
            except Exception as error:
                formulario = {"error": str(error)}
            formularios = [
                item for item in formularios if item.get("convocatoria") != referencia
            ]
            formularios.append({"convocatoria": referencia, "formulario": formulario})
            ya.add(referencia)
            _guardar(formularios)
            print(f"postular {indice + 1}/{len(referencias)} {referencia}", flush=True)
        for indice, item in enumerate(pendientes):
            _volver(page)
            try:
                boton = next(
                    candidato for candidato in _postulaciones(page)
                    if candidato["nombre"] == item["nombre"]
                )
                formulario = _abrir_postulacion(page, boton["id"])
            except Exception as error:
                formulario = {"error": str(error)}
            formularios.append({"convocatoria": item["nombre"], "formulario": formulario})
            ya.add(item["nombre"])
            _guardar(formularios)
            print(f"postulacion {indice + 1}/{len(pendientes)} {item['nombre']}", flush=True)
        _borrar_en_proceso(page)
        browser.close()

    print(SALIDA)


if __name__ == "__main__":
    main()
