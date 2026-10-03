// Muestra el campo de texto "Especificá tu rol" solo cuando eligen "Otros".
(function () {
  const select = document.getElementById("perfil");
  const campoOtro = document.querySelector("[data-perfil-otro]");
  const inputOtro = document.getElementById("perfilOtro");

  if (!select || !campoOtro || !inputOtro) {
    return;
  }

  function sincronizar() {
    const esOtro = select.value === "Otros";
    campoOtro.hidden = !esOtro;
    inputOtro.required = esOtro;
    if (!esOtro) {
      inputOtro.value = "";
    }
  }

  select.addEventListener("change", sincronizar);
  sincronizar();
})();
