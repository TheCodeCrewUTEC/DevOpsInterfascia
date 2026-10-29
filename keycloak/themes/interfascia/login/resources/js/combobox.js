// Mismo comportamiento que el componente Combobox de la app: cada <select> del
// formulario pasa a ser un campo donde se escribe para filtrar las opciones
// (sin importar tildes ni mayúsculas). El <select> real queda oculto dentro,
// así se sigue enviando y lo siguen usando addable-select.js, rol-otro.js y
// required-fields.js. Los eventos van delegados en document porque
// addable-select.js clona filas enteras.
(function () {
  const ingles = (document.documentElement.lang || "").toLowerCase().startsWith("en");
  const sinCoincidencias = ingles ? "No matches" : "Sin coincidencias";

  function normalizar(texto) {
    return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
  }

  function partes(combo) {
    return {
      select: combo.querySelector("select"),
      input: combo.querySelector(".ifx-combo__input"),
      lista: combo.querySelector(".ifx-combo__list"),
    };
  }

  // Las opciones que addable-select.js oculta (ya elegidas en otra fila) no se ofrecen
  function opcionesDisponibles(select) {
    return [...select.options].filter((opcion) => opcion.value && !opcion.disabled && !opcion.hidden);
  }

  function textoElegido(select) {
    const opcion = select.options[select.selectedIndex];
    return opcion && opcion.value ? opcion.textContent.trim() : "";
  }

  function placeholderDe(select) {
    const vacia = [...select.options].find((opcion) => !opcion.value);
    return vacia ? vacia.textContent.trim() : "";
  }

  function mejorar(select) {
    if (select.closest(".ifx-combo")) return;

    const combo = document.createElement("div");
    combo.className = "ifx-combo";
    select.parentNode.insertBefore(combo, select);
    combo.appendChild(select);
    select.tabIndex = -1;

    const input = document.createElement("input");
    input.type = "text";
    input.className = "ifx-combo__input";
    input.autocomplete = "off";
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-expanded", "false");

    const etiqueta = select.closest(".ifx-field")?.querySelector("label");
    if (etiqueta) input.setAttribute("aria-label", etiqueta.textContent.replace("*", "").trim());

    const lista = document.createElement("ul");
    lista.className = "ifx-combo__list";
    lista.setAttribute("role", "listbox");
    lista.hidden = true;

    combo.append(input, lista);
    refrescar(combo);
  }

  function refrescar(combo) {
    const { select, input } = partes(combo);
    input.placeholder = placeholderDe(select);
    input.value = textoElegido(select);
  }

  function pintarLista(combo, filtro) {
    const { select, input, lista } = partes(combo);
    const buscado = normalizar(filtro || "");
    const visibles = opcionesDisponibles(select).filter(
      (opcion) => !buscado || normalizar(opcion.textContent).includes(buscado),
    );

    lista.innerHTML = "";

    if (visibles.length === 0) {
      const vacio = document.createElement("li");
      vacio.className = "ifx-combo__vacio";
      vacio.textContent = sinCoincidencias;
      lista.appendChild(vacio);
    }

    let activa = visibles.findIndex((opcion) => opcion.value === select.value);
    if (activa < 0 || buscado) activa = 0;

    visibles.forEach((opcion, indice) => {
      const item = document.createElement("li");
      item.className = "ifx-combo__option";
      item.setAttribute("role", "option");
      item.dataset.valor = opcion.value;
      item.dataset.activa = String(indice === activa);
      item.setAttribute("aria-selected", String(opcion.value === select.value));
      item.textContent = opcion.textContent.trim();
      lista.appendChild(item);
    });

    lista.hidden = false;
    input.setAttribute("aria-expanded", "true");
    lista.querySelector('[data-activa="true"]')?.scrollIntoView({ block: "nearest" });
  }

  function cerrar(combo) {
    const { input, lista } = partes(combo);
    lista.hidden = true;
    input.setAttribute("aria-expanded", "false");
    // Lo escrito que no coincide con ninguna opción no queda elegido
    refrescar(combo);
  }

  function elegir(combo, valor) {
    const { select } = partes(combo);
    if (select.value !== valor) {
      select.value = valor;
      select.dispatchEvent(new Event("change", { bubbles: true }));
    }
    cerrar(combo);
  }

  function moverActiva(combo, delta) {
    const items = [...partes(combo).lista.querySelectorAll(".ifx-combo__option")];
    if (items.length === 0) return;
    const actual = items.findIndex((item) => item.dataset.activa === "true");
    const siguiente = Math.max(0, Math.min(items.length - 1, actual + delta));
    items.forEach((item, indice) => (item.dataset.activa = String(indice === siguiente)));
    items[siguiente].scrollIntoView({ block: "nearest" });
  }

  document.addEventListener("click", (evento) => {
    const input = evento.target.closest?.(".ifx-combo__input");
    if (input && partes(input.closest(".ifx-combo")).lista.hidden) {
      pintarLista(input.closest(".ifx-combo"), "");
    }
  });

  document.addEventListener("input", (evento) => {
    const input = evento.target.closest?.(".ifx-combo__input");
    if (input) pintarLista(input.closest(".ifx-combo"), input.value);
  });

  document.addEventListener("keydown", (evento) => {
    const input = evento.target.closest?.(".ifx-combo__input");
    if (!input) return;
    const combo = input.closest(".ifx-combo");
    const { lista } = partes(combo);

    if (evento.key === "ArrowDown" || evento.key === "ArrowUp") {
      evento.preventDefault();
      if (lista.hidden) pintarLista(combo, "");
      else moverActiva(combo, evento.key === "ArrowDown" ? 1 : -1);
    } else if (evento.key === "Enter" && !lista.hidden) {
      evento.preventDefault();
      const activa = lista.querySelector('.ifx-combo__option[data-activa="true"]');
      if (activa) elegir(combo, activa.dataset.valor);
    } else if (evento.key === "Escape" && !lista.hidden) {
      evento.preventDefault();
      cerrar(combo);
    }
  });

  // mousedown (no click) para elegir antes de que el blur cierre la lista
  document.addEventListener("mousedown", (evento) => {
    const opcion = evento.target.closest?.(".ifx-combo__option");
    if (!opcion) return;
    evento.preventDefault();
    elegir(opcion.closest(".ifx-combo"), opcion.dataset.valor);
  });

  // El mouse mueve el resaltado igual que las flechas
  document.addEventListener("mouseover", (evento) => {
    const opcion = evento.target.closest?.(".ifx-combo__option");
    if (!opcion) return;
    opcion.parentElement
      .querySelectorAll(".ifx-combo__option")
      .forEach((item) => (item.dataset.activa = String(item === opcion)));
  });

  document.addEventListener("focusin", (evento) => {
    const input = evento.target.closest?.(".ifx-combo__input");
    if (input) {
      input.select();
      return;
    }
    // El label y required-fields.js enfocan el <select> oculto: se pasa al input
    if (evento.target instanceof HTMLSelectElement && evento.target.parentElement?.classList.contains("ifx-combo")) {
      partes(evento.target.parentElement).input.focus();
    }
  });

  document.addEventListener("focusout", (evento) => {
    const input = evento.target.closest?.(".ifx-combo__input");
    if (input) cerrar(input.closest(".ifx-combo"));
  });

  // Si otro script cambia el select (p. ej. al quitar una fila), el texto lo acompaña
  document.addEventListener("change", (evento) => {
    if (evento.target instanceof HTMLSelectElement && evento.target.parentElement?.classList.contains("ifx-combo")) {
      refrescar(evento.target.parentElement);
    }
  });

  // addable-select.js lo llama después de agregar o quitar filas
  window.ifxComboRefrescar = function (contenedor) {
    (contenedor || document).querySelectorAll(".ifx-combo").forEach((combo) => {
      cerrar(combo);
    });
  };

  document.querySelectorAll(".ifx-field select").forEach(mejorar);
})();
