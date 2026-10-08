// Agrega un botón con un ojo a cada campo de contraseña para ver lo que se escribe.
(function () {
  const ingles = (document.documentElement.lang || "").toLowerCase().startsWith("en");
  const textos = ingles
    ? { mostrar: "Show password", ocultar: "Hide password" }
    : { mostrar: "Mostrar contraseña", ocultar: "Ocultar contraseña" };

  const ojo =
    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>';
  const ojoTachado =
    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M10.6 5.1A10.7 10.7 0 0 1 12 5c6.4 0 10 7 10 7a17.6 17.6 0 0 1-2.6 3.4"/>' +
    '<path d="M6.6 6.6C3.7 8.4 2 12 2 12s3.6 7 10 7a9.6 9.6 0 0 0 5.4-1.6"/>' +
    '<path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/><path d="m3 3 18 18"/></svg>';

  document.querySelectorAll('input[type="password"]').forEach((input) => {
    const contenedor = document.createElement("div");
    contenedor.className = "ifx-password";
    input.parentNode.insertBefore(contenedor, input);
    contenedor.appendChild(input);

    const boton = document.createElement("button");
    boton.type = "button";
    boton.className = "ifx-password__toggle";
    boton.setAttribute("aria-controls", input.id);

    function pintar(visible) {
      boton.innerHTML = visible ? ojoTachado : ojo;
      boton.setAttribute("aria-label", visible ? textos.ocultar : textos.mostrar);
      boton.setAttribute("aria-pressed", String(visible));
      boton.title = visible ? textos.ocultar : textos.mostrar;
    }

    boton.addEventListener("click", () => {
      const visible = input.type === "password";
      input.type = visible ? "text" : "password";
      pintar(visible);
      input.focus();
    });

    // Al enviar vuelve a ser password, así el navegador ofrece guardar la contraseña
    input.form?.addEventListener("submit", () => {
      input.type = "password";
      pintar(false);
    });

    pintar(false);
    contenedor.appendChild(boton);
  });
})();
