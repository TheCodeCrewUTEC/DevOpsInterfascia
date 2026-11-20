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
    if os.environ.get("ANDE_DEPENDENCIAS") == "1":
        _anotar_dependencias(frame, formulario)
    _agrupar_tablas(formulario)
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
            let tituloH5 = "";
            let tituloH6 = "";
            let h5Pendiente = false;
            let h6Pendiente = false;
            const detalleDe = () => [tituloH5, tituloH6].filter(Boolean).join("\\n");
            for (const el of document.querySelectorAll("h1, h2, h3, h4, h5, h6, legend, input, textarea, select")) {
                if (/^H[1-6]$/.test(el.tagName) || el.tagName === "LEGEND") {
                    const titulo = limpio(el.innerText).slice(0, 400);
                    if (!titulo) continue;
                    const nivel = el.tagName === "LEGEND" ? 4 : Number(el.tagName.slice(1));
                    if (nivel <= 4) {
                        seccion = titulo;
                        if (!h5Pendiente) tituloH5 = "";
                        if (!h6Pendiente) tituloH6 = "";
                        h5Pendiente = false;
                        h6Pendiente = false;
                    } else if (nivel === 5) {
                        tituloH5 = titulo;
                        tituloH6 = "";
                        h5Pendiente = true;
                        h6Pendiente = false;
                    } else {
                        tituloH6 = titulo;
                        h6Pendiente = true;
                    }
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
                    detalle: detalleDe(),
                    etiqueta,
                    tipo: tipoDe(el),
                    requerido: Boolean(el.required || etiqueta.endsWith("*")),
                    opciones,
                    selector,
                });
                h5Pendiente = false;
                h6Pendiente = false;
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


_CATALOGOS = []

_LEER_PARES = """() => {
    const pares = [];
    const vistos = new Set();
    const sumar = (padre, hijo) => {
        const limpio = (valor) => String(valor || "").replace(/\\\\/g, "");
        padre = limpio(padre);
        hijo = limpio(hijo);
        if (!padre || !hijo || padre === hijo) return;
        const clave = padre + "\\0" + hijo;
        if (vistos.has(clave)) return;
        vistos.add(clave);
        pares.push({ padre, hijo });
    };
    if (window.jQuery) {
        for (const select of document.querySelectorAll("select")) {
            const data = window.jQuery._data(select, "events");
            for (const cambio of (data && data.change) || []) {
                const fuente = String(cambio.handler);
                const re = /selectAutoLoadedScript\\s*\\(\\s*event\\s*,\\s*['"]([^'"]+)['"]/g;
                let match;
                while ((match = re.exec(fuente))) sumar(select.id, match[1]);
            }
        }
    }
    const scripts = [...document.scripts].map((script) => script.textContent || "").join("\\n");
    const reScript = /\\$\\(\\s*['"]#([^'"]+)['"]\\s*\\)\\s*\\.on\\(\\s*['"]change['"][\\s\\S]{0,500}?selectAutoLoadedScript\\(\\s*event\\s*,\\s*['"]([^'"]+)['"]/g;
    let match;
    while ((match = reScript.exec(scripts))) sumar(match[1], match[2]);
    return pares;
}"""


def _es_fila(campo):
    selector = str((campo or {}).get("selector") or "")
    prefijo = selector.split("·", 1)[0]
    return "·" in selector and prefijo.startswith("n") and prefijo[1:].isdigit()


def _agrupar_tablas(formulario):
    """Junta la fila plantilla de un repetidor (n1·…) en un solo campo tabla.

    En el portal el usuario agrega filas. Acá queda la definición de las columnas.
    """
    campos = formulario.get("campos") or []
    agrupados = []
    indice = 0
    while indice < len(campos):
        campo = campos[indice]
        if not isinstance(campo, dict) or not _es_fila(campo):
            agrupados.append(campo)
            indice += 1
            continue
        seccion = campo.get("seccion") or "General"
        columnas = []
        while indice < len(campos):
            actual = campos[indice]
            if (
                not isinstance(actual, dict)
                or actual.get("seccion") != seccion
                or not _es_fila(actual)
            ):
                break
            columnas.append(
                {
                    "etiqueta": actual.get("etiqueta"),
                    "tipo": actual.get("tipo") or "text",
                    "requerido": bool(actual.get("requerido")),
                    "opciones": actual.get("opciones") or [],
                    "selector": actual.get("selector"),
                    "depende_de": actual.get("depende_de"),
                    "opciones_por_valor": actual.get("opciones_por_valor") or {},
                    "detalle": actual.get("detalle") or "",
                }
            )
            indice += 1
        requerido = any(columna["requerido"] for columna in columnas)
        titulo = seccion.rstrip("*").strip()
        agrupados.append(
            {
                "seccion": seccion,
                "detalle": next(
                    (columna.get("detalle") for columna in columnas if columna.get("detalle")),
                    "",
                ),
                "etiqueta": f"{titulo} *" if requerido else titulo,
                "tipo": "tabla",
                "requerido": requerido,
                "opciones": [],
                "selector": f"tabla:{columnas[0]['selector']}",
                "columnas": columnas,
            }
        )
    formulario["campos"] = agrupados


def _familia_padre(selector):
    limpio = selector.lower().replace("·", "").replace("_", "")
    if "ciiu" in limpio and "4" not in limpio:
        return "ciiu"
    if "localidad" in limpio:
        return ""
    if limpio.startswith("dep") or "departamento" in limpio or "dep" in limpio:
        return "lugar"
    return ""


def _familia_hijo(selector):
    limpio = selector.lower().replace("·", "").replace("_", "")
    if "ciiu" in limpio and "4" in limpio:
        return "ciiu"
    if "localidad" in limpio:
        return "lugar"
    return ""


def _por_id(frame, elemento_id):
    return frame.locator(f"[id={json.dumps(elemento_id)}]")


def _textos_opciones(frame, elemento_id):
    locator = _por_id(frame, elemento_id)
    if locator.count() == 0:
        return []
    return locator.evaluate(
        """(el) => [...el.options]
            .map((opcion) => (opcion.textContent || "").replace(/\\s+/g, " ").trim())
            .filter((texto) => texto && !texto.startsWith("--"))"""
    )


def _catalogo_para(familia, opciones):
    buscadas = [texto for texto in opciones if texto]
    if not familia or not buscadas:
        return None
    mejor = None
    for item in _CATALOGOS:
        if item["familia"] != familia:
            continue
        if all(texto in item["mapa"] for texto in buscadas):
            return item["mapa"]
        comunes = sum(1 for texto in buscadas if texto in item["mapa"])
        if mejor is None or comunes > mejor[0]:
            mejor = (comunes, item["mapa"])
    if mejor and mejor[0] >= max(1, len(buscadas) // 2):
        return mejor[1]
    return None


def _guardar_catalogo(familia, mapa):
    if not familia or not any(mapa.values()):
        return
    firma = tuple(mapa)
    for item in _CATALOGOS:
        if item["familia"] == familia and item["firma"] == firma:
            return
    _CATALOGOS.append({"familia": familia, "firma": firma, "mapa": mapa})


def _anotar_dependencias(frame, formulario):
    frame.evaluate(
        """() => {
            if (typeof autoSave === "function") window.autoSave = () => {};
        }"""
    )
    pares = frame.evaluate(_LEER_PARES)
    print(f"pares {len(pares)}", flush=True)
    if not pares:
        muestra = frame.evaluate(
            """() => {
                const texto = [...document.scripts].map((script) => script.textContent || "").join("\\n");
                const indice = texto.indexOf("selectAutoLoadedScript");
                return indice < 0 ? "" : texto.slice(Math.max(0, indice - 180), indice + 240);
            }"""
        )
        print(f"sin pares {muestra[:400]}", flush=True)
        return
    por_selector = {
        campo.get("selector"): campo
        for campo in formulario.get("campos") or []
        if isinstance(campo, dict)
    }
    for par in pares:
        padre = por_selector.get(par["padre"])
        hijo = por_selector.get(par["hijo"])
        if not padre or not hijo:
            continue
        try:
            mapa = _mapa_dependiente(frame, par["padre"], par["hijo"], padre.get("opciones") or [])
        except Exception as error:
            print(f"sin lista {par['padre']} -> {par['hijo']}: {error}", flush=True)
            continue
        if not mapa:
            continue
        hijo["depende_de"] = par["padre"]
        hijo["opciones_por_valor"] = mapa


def _mapa_dependiente(frame, padre_id, hijo_id, opciones_conocidas):
    familia = _familia_padre(padre_id)
    reusado = _catalogo_para(familia, opciones_conocidas)
    if reusado and all(texto in reusado for texto in opciones_conocidas if texto):
        print(f"reuso {padre_id} -> {hijo_id}", flush=True)
        return {texto: reusado[texto] for texto in opciones_conocidas if texto in reusado}
    if _por_id(frame, padre_id).count() == 0:
        return None
    opciones = _por_id(frame, padre_id).evaluate(
        """(el) => [...el.options].map((opcion, indice) => ({
            indice,
            texto: (opcion.textContent || "").replace(/\\s+/g, " ").trim(),
        })).filter((opcion) => opcion.texto && !opcion.texto.startsWith("--"))"""
    )
    mapa = {}
    fallos = 0
    for opcion in opciones:
        textos = _cargar_hijo(frame, padre_id, hijo_id, opcion["indice"])
        mapa[opcion["texto"]] = textos
        print(f"{padre_id}: {opcion['texto'][:48]} -> {len(textos)}", flush=True)
        if textos:
            fallos = 0
        else:
            fallos += 1
            if fallos >= 2 and not any(mapa.values()):
                print(f"corto {padre_id} -> {hijo_id}", flush=True)
                break
    _guardar_catalogo(familia, mapa)
    return mapa


def _cargar_hijo(frame, padre_id, hijo_id, indice):
    frame.evaluate(
        """(id) => {
            const hijo = document.getElementById(id);
            if (!hijo) return;
            hijo.innerHTML = '<option value="">--Seleccionar--</option>';
        }""",
        hijo_id,
    )
    try:
        _por_id(frame, padre_id).select_option(index=indice)
    except Exception:
        return []
    try:
        frame.wait_for_function(
            """(id) => {
                const hijo = document.getElementById(id);
                if (!hijo) return false;
                return [...hijo.options].some((opcion) => {
                    const texto = (opcion.textContent || "").trim();
                    return texto && !texto.startsWith("--");
                });
            }""",
            arg=hijo_id,
            timeout=12000,
        )
    except PlaywrightTimeout:
        frame.evaluate(
            """([padreId, hijoId, indice]) => {
                const select = document.getElementById(padreId);
                if (!select) return;
                select.selectedIndex = indice;
                const nativo = new Event("change", { bubbles: true });
                window.event = nativo;
                Object.defineProperty(nativo, "currentTarget", { value: select });
                const data = window.jQuery && window.jQuery._data(select, "events");
                const cambios = (data && data.change) || [];
                for (const cambio of cambios) cambio.handler.call(select, nativo);
            }""",
            [padre_id, hijo_id, indice],
        )
        try:
            frame.wait_for_function(
                """(id) => {
                    const hijo = document.getElementById(id);
                    if (!hijo) return false;
                    return [...hijo.options].some((opcion) => {
                        const texto = (opcion.textContent || "").trim();
                        return texto && !texto.startsWith("--");
                    });
                }""",
                arg=hijo_id,
                timeout=8000,
            )
        except PlaywrightTimeout:
            return []
    return _textos_opciones(frame, hijo_id)


def _aplicar_catalogos(formularios):
    if not _CATALOGOS:
        return
    for item in formularios:
        campos = (item.get("formulario") or {}).get("campos") or []
        ultimo = {"ciiu": None, "lugar": None}
        for campo in campos:
            if not isinstance(campo, dict):
                continue
            selector = campo.get("selector") or ""
            opciones = campo.get("opciones") or []
            familia_padre = _familia_padre(selector)
            if familia_padre and opciones:
                ultimo[familia_padre] = campo
            if campo.get("opciones_por_valor"):
                continue
            familia = _familia_hijo(selector)
            padre = ultimo.get(familia) if familia else None
            if not padre:
                continue
            mapa = _catalogo_para(familia, padre.get("opciones") or [])
            if not mapa:
                continue
            campo["depende_de"] = padre.get("selector")
            campo["opciones_por_valor"] = {
                texto: mapa[texto]
                for texto in padre.get("opciones") or []
                if texto in mapa
            }


def _borrar_prueba(page):
    _volver(page)
    while True:
        pendiente = page.evaluate(
            """() => {
                const limpio = (texto) => (texto || "").replace(/\\s+/g, " ").trim();
                const boton = [...document.querySelectorAll('a[title="Borrar postulación"]')]
                    .find((el) => {
                        const fila = el.closest("tr");
                        return !el.id.includes("Mb") && /\\bPrueba\\b/.test(limpio(fila && fila.innerText));
                    });
                if (!boton) return null;
                return { id: boton.id, texto: limpio(boton.closest("tr").innerText) };
            }"""
        )
        if not pendiente:
            break
        page.evaluate("(id) => document.getElementById(id).click()", pendiente["id"])
        page.wait_for_function(
            """() => document.querySelector("#modalDeleteSubmission")?.classList.contains("show")""",
            timeout=10000,
        )
        page.locator("[id='modalDeleteSubmissionForm:mdsYBtn']").click()
        try:
            page.wait_for_function(
                """(texto) => {
                    const limpio = (valor) => (valor || "").replace(/\\s+/g, " ").trim();
                    const modal = document.querySelector("#modalDeleteSubmission");
                    const filas = [...document.querySelectorAll('a[title="Borrar postulación"]')]
                        .filter((el) => !el.id.includes("Mb"))
                        .map((el) => limpio(el.closest("tr") && el.closest("tr").innerText));
                    return (!modal || !modal.classList.contains("show")) && !filas.includes(texto);
                }""",
                arg=pendiente["texto"],
                timeout=15000,
            )
        except PlaywrightTimeout:
            _volver(page)
        print(f"borrada {pendiente['texto']}", flush=True)


def _catalogos_listos():
    familias = {item["familia"] for item in _CATALOGOS}
    return "ciiu" in familias and "lugar" in familias


def _completar_dependencias():
    email, password = _credenciales()
    headless = os.environ.get("ANDE_HEADFUL", "") != "1"
    formularios = _cargar()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context(locale="es-UY", viewport={"width": 1400, "height": 1200})
        page = context.new_page()
        _login(page, email, password)
        try:
            referencias = _convocatorias(page)
            for indice, referencia in enumerate(referencias):
                if _catalogos_listos():
                    break
                if indice:
                    _volver(page)
                try:
                    formulario = _abrir(page, referencia)
                except Exception as error:
                    print(f"salteo {referencia}: {error}", flush=True)
                    continue
                if formulario.get("error"):
                    print(f"salteo {referencia}: {formulario['error']}", flush=True)
                    continue
                formularios = [
                    item for item in formularios if item.get("convocatoria") != referencia
                ]
                formularios.append({"convocatoria": referencia, "formulario": formulario})
                _guardar(formularios)
                print(f"dependencias {referencia}", flush=True)
            _aplicar_catalogos(formularios)
            _guardar(formularios)
        finally:
            try:
                _borrar_prueba(page)
            except Exception as error:
                print(f"no pude borrar el borrador Prueba: {error}", flush=True)
            browser.close()
    print(SALIDA)


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
    if os.environ.get("ANDE_DEPENDENCIAS") == "1":
        _completar_dependencias()
        return
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
