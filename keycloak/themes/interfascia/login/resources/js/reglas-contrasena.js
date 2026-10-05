// Tilda los requisitos de la contraseña mientras se escribe.
// Mismas reglas que la passwordPolicy del realm: length(12), digits(1), upperCase(1),
// specialChars(1). Para Keycloak, "especial" es todo lo que no es letra ni número.
(function () {
  const input = document.getElementById("password");
  const lista = document.querySelector("[data-reglas-password]");

  if (!input || !lista) {
    return;
  }

  const reglas = {
    largo: (valor) => valor.length >= 12,
    numero: (valor) => /\p{Nd}/u.test(valor),
    mayuscula: (valor) => /\p{Lu}/u.test(valor),
    especial: (valor) => /[^\p{L}\p{N}]/u.test(valor),
  };

  function actualizar() {
    for (const item of lista.querySelectorAll("[data-regla]")) {
      const cumple = reglas[item.dataset.regla]?.(input.value) ?? false;
      item.classList.toggle("cumple", cumple);
    }
  }

  input.addEventListener("input", actualizar);
  actualizar();
})();
