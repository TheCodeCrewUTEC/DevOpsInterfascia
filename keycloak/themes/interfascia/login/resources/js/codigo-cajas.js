// Reemplaza el campo del código de verificación por una caja por dígito.
// El input original (name="code") queda oculto y es el que se envía; sin JavaScript
// se sigue usando como un campo de texto normal.
//
// Se carga sin defer, justo después del formulario, para registrar la validación del
// envío antes que required-fields.js.
(function () {
  const form = document.getElementById("kc-email-code-form");
  const original = document.getElementById("code");

  if (!form || !original) {
    return;
  }

  const largo = Number(original.getAttribute("maxlength")) || 6;
  const etiqueta = original.dataset.etiquetaDigito || "Dígito";
  const conError = original.getAttribute("aria-invalid") === "true";

  const grupo = document.createElement("div");
  grupo.className = "ifx-otp";
  grupo.setAttribute("role", "group");

  const label = form.querySelector('label[for="code"]');
  if (label) {
    label.id = "code-label";
    label.htmlFor = "code-1";
    grupo.setAttribute("aria-labelledby", "code-label");
  }

  const cajas = [];

  for (let i = 0; i < largo; i++) {
    const caja = document.createElement("input");
    caja.id = `code-${i + 1}`;
    caja.className = "ifx-otp__box";
    caja.type = "text";
    caja.inputMode = "numeric";
    caja.maxLength = 1;
    caja.dir = "ltr";
    // Solo la primera: el autocompletado del sistema pega el código entero ahí
    caja.autocomplete = i === 0 ? "one-time-code" : "off";
    caja.setAttribute("aria-label", `${etiqueta} ${i + 1}/${largo}`);
    if (conError) caja.setAttribute("aria-invalid", "true");
    cajas.push(caja);
    grupo.appendChild(caja);
  }

  // El original pasa a ser oculto: no se valida ni se muestra, solo se envía
  original.type = "hidden";
  original.removeAttribute("required");
  original.removeAttribute("pattern");
  original.removeAttribute("autofocus");
  original.insertAdjacentElement("afterend", grupo);

  function sincronizar() {
    original.value = cajas.map((caja) => caja.value).join("");
  }

  function marcarError(activo) {
    for (const caja of cajas) {
      const invalida = activo && caja.value === "";
      caja.setAttribute("aria-invalid", invalida ? "true" : "false");
    }
  }

  // Reparte varios dígitos desde una caja (pegar o autocompletar)
  function repartir(desde, texto) {
    const digitos = texto.replace(/\D/g, "").slice(0, largo - desde);
    [...digitos].forEach((digito, i) => {
      cajas[desde + i].value = digito;
    });
    sincronizar();
    const siguiente = cajas.find((caja) => caja.value === "") ?? cajas[largo - 1];
    siguiente.focus();
  }

  cajas.forEach((caja, i) => {
    caja.addEventListener("focus", () => caja.select());

    caja.addEventListener("input", () => {
      if (caja.value.length > 1) {
        repartir(i, caja.value);
        return;
      }

      caja.value = caja.value.replace(/\D/g, "");
      sincronizar();
      marcarError(false);

      if (caja.value && i < largo - 1) {
        cajas[i + 1].focus();
      }
    });

    caja.addEventListener("keydown", (event) => {
      if (event.key === "Backspace" && caja.value === "" && i > 0) {
        event.preventDefault();
        cajas[i - 1].value = "";
        cajas[i - 1].focus();
        sincronizar();
      } else if (event.key === "ArrowLeft" && i > 0) {
        event.preventDefault();
        cajas[i - 1].focus();
      } else if (event.key === "ArrowRight" && i < largo - 1) {
        event.preventDefault();
        cajas[i + 1].focus();
      }
    });

    caja.addEventListener("paste", (event) => {
      const texto = event.clipboardData?.getData("text") ?? "";
      if (!texto) return;
      event.preventDefault();
      repartir(/\d{2,}/.test(texto) ? 0 : i, texto);
      marcarError(false);
    });
  });

  // Captura y antes que required-fields.js: si faltan dígitos no se envía
  form.addEventListener(
    "submit",
    (event) => {
      sincronizar();
      if (original.value.length === largo) return;

      event.preventDefault();
      event.stopImmediatePropagation();
      marcarError(true);
      (cajas.find((caja) => caja.value === "") ?? cajas[0]).focus();
    },
    true,
  );

  cajas[0].focus();
})();
