// Mismo comportamiento que el componente AddableSelect de la app:
// el botón "+" agrega otro select para elegir un valor más.
document.querySelectorAll("[data-addable-select]").forEach((campo) => {
  campo.addEventListener("click", (event) => {
    const boton = event.target.closest(".ifx-addable__add");

    if (!boton) {
      return;
    }

    const filas = campo.querySelectorAll(".ifx-addable__row");
    const ultima = filas[filas.length - 1];
    const nueva = ultima.cloneNode(true);
    const select = nueva.querySelector("select");

    select.id = `${select.name}-${filas.length}`;
    select.required = false;
    select.removeAttribute("aria-invalid");
    select.selectedIndex = 0;

    ultima.after(nueva);
    select.focus();
  });
});

// Los selects extra que quedaron sin elegir no se envían
const formulario = document.getElementById("kc-register-form");

formulario?.addEventListener("submit", () => {
  formulario
    .querySelectorAll("[data-addable-select] .ifx-addable__row:not(:first-of-type) select")
    .forEach((select) => {
      if (!select.value) {
        select.disabled = true;
      }
    });
});
