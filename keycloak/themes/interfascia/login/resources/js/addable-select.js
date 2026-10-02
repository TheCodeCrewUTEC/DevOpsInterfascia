// Mismo comportamiento que el componente AddableSelect de la app:
// "+" agrega otro select, "×" quita uno, y una opción usada no se ofrece
// en los demás. Al quitarla, vuelve a estar disponible.
document.querySelectorAll("[data-addable-select]").forEach((campo) => {
  campo.addEventListener("click", (event) => {
    if (event.target.closest(".ifx-addable__add")) {
      agregarFila(campo);
      return;
    }

    const quitar = event.target.closest(".ifx-addable__remove");
    if (quitar) {
      quitarFila(campo, quitar.closest(".ifx-addable__row"));
    }
  });

  campo.addEventListener("change", (event) => {
    if (event.target instanceof HTMLSelectElement) {
      sincronizar(campo);
    }
  });

  sincronizar(campo);
});

function filasDe(campo) {
  return [...campo.querySelectorAll(".ifx-addable__row")];
}

function opcionesReales(select) {
  return [...select.options].filter((opcion) => opcion.value);
}

function sincronizar(campo) {
  const filas = filasDe(campo);
  const selects = filas.map((fila) => fila.querySelector("select"));
  const elegidos = selects.map((select) => select.value).filter(Boolean);
  const total = opcionesReales(selects[0]).length;
  const puedeAgregar =
    selects.every((select) => select.value) && new Set(elegidos).size < total;

  const etiqueta = campo.querySelector("label");
  const obligatorio = campo.dataset.required === "true";

  filas.forEach((fila, index) => {
    const select = selects[index];
    select.id = `${select.name}-${index}`;
    select.required = obligatorio && index === 0;

    for (const opcion of opcionesReales(select)) {
      const ocupada = opcion.value !== select.value && elegidos.includes(opcion.value);
      opcion.disabled = ocupada;
      opcion.hidden = ocupada;
    }

    const quitar = fila.querySelector(".ifx-addable__remove");
    if (quitar) {
      quitar.hidden = !select.value && filas.length === 1;
    }

    const agregar = fila.querySelector(".ifx-addable__add");
    if (agregar) {
      agregar.hidden = index !== filas.length - 1 || !puedeAgregar;
    }
  });

  if (etiqueta && selects[0]) {
    etiqueta.htmlFor = selects[0].id;
  }
}

function prepararSelectNuevo(select, indice) {
  select.id = `${select.name}-${indice}`;
  select.required = false;
  select.removeAttribute("aria-invalid");

  for (const opcion of select.options) {
    opcion.disabled = !opcion.value;
    opcion.hidden = false;
  }

  // El placeholder está disabled: selectedIndex sí lo deja elegido.
  select.selectedIndex = 0;
}

function agregarFila(campo) {
  const filas = filasDe(campo);
  const ultima = filas[filas.length - 1];
  const nueva = ultima.cloneNode(true);
  const select = nueva.querySelector("select");

  prepararSelectNuevo(select, filas.length);
  ultima.after(nueva);
  sincronizar(campo);
  select.focus();
}

function quitarFila(campo, fila) {
  const filas = filasDe(campo);
  const select = fila.querySelector("select");

  if (filas.length > 1) {
    fila.remove();
  } else {
    prepararSelectNuevo(select, 0);
  }

  sincronizar(campo);
  const siguiente = campo.querySelector("select");
  siguiente?.focus();
}

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
