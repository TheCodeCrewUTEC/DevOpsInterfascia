// Misma validación que las páginas de login y registro de la app:
// al enviar, los campos obligatorios vacíos se marcan en rojo.
document.querySelectorAll("form").forEach((form) => {
  form.noValidate = true;

  const banner = form.closest(".ifx-card, .ifx-register__panel")?.querySelector("[data-required-banner]");
  let attempted = false;

  function controls() {
    return [...form.querySelectorAll("input, select, textarea")].filter((element) => {
      if (element.disabled || element.type === "hidden" || element.type === "submit" || element.type === "button") {
        return false;
      }
      return element.required || element.getAttribute("aria-required") === "true";
    });
  }

  function isEmpty(element) {
    if (element.type === "checkbox" || element.type === "radio") {
      return ![...form.querySelectorAll(`[name="${CSS.escape(element.name)}"]`)].some((item) => item.checked);
    }
    return String(element.value).trim() === "";
  }

  function missingNames() {
    const groups = new Map();
    for (const element of controls()) {
      if (!groups.has(element.name)) groups.set(element.name, []);
      groups.get(element.name).push(element);
    }

    return [...groups.entries()]
      .filter(([, elements]) => elements.every(isEmpty))
      .map(([name]) => name);
  }

  function paint() {
    const missing = new Set(missingNames());

    for (const element of form.querySelectorAll("input, select, textarea")) {
      if (element.type === "hidden" || element.type === "submit" || element.type === "button") continue;
      const invalid = missing.has(element.name) && isEmpty(element);
      element.setAttribute("aria-invalid", invalid ? "true" : "false");
    }

    if (banner) banner.hidden = missing.size === 0;
    return missing;
  }

  form.addEventListener("submit", (event) => {
    attempted = true;
    const missing = paint();
    if (missing.size === 0) {
      const submit = event.submitter instanceof HTMLButtonElement ? event.submitter : form.querySelector("[type='submit']");
      if (submit) {
        setTimeout(() => {
          submit.disabled = true;
        }, 0);
      }
      return;
    }

    event.preventDefault();
    event.stopImmediatePropagation();
    const first = form.elements.namedItem(missing[0]);
    const field = first instanceof RadioNodeList ? first[0] : first;
    if (field instanceof HTMLElement) field.focus();
  }, true);

  form.addEventListener("input", () => {
    if (attempted) paint();
  });

  form.addEventListener("change", () => {
    if (attempted) paint();
  });
});
