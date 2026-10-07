// Tilda los requisitos de la contraseña mientras se escribe.
// Mismas reglas que la passwordPolicy del realm: length(12) y complejidad(3), o sea 3 de las 4
// categorías (mayúscula, minúscula, número, especial). Para Keycloak, "especial" es todo lo que
// no es letra ni número.
(function () {
  const input = document.getElementById("password");
  const lista = document.querySelector("[data-reglas-password]");

  if (!input || !lista) {
    return;
  }

  const CATEGORIAS_MINIMAS = 3;
  const categorias = {
    mayuscula: (valor) => /\p{Lu}/u.test(valor),
    minuscula: (valor) => /\p{Ll}/u.test(valor),
    numero: (valor) => /\p{Nd}/u.test(valor),
    especial: (valor) => /[^\p{L}\p{N}]/u.test(valor),
  };

  const reglas = {
    ...categorias,
    largo: (valor) => valor.length >= 12,
    complejidad: (valor) =>
      Object.values(categorias).filter((cumple) => cumple(valor)).length >= CATEGORIAS_MINIMAS,
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
