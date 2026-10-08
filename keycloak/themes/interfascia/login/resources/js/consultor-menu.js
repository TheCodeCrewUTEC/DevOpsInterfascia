document.addEventListener("click", (evento) => {
  document.querySelectorAll(".ifx-navbar__menu[open]").forEach((menu) => {
    if (!menu.contains(evento.target)) menu.removeAttribute("open");
  });
});

document.addEventListener("keydown", (evento) => {
  if (evento.key !== "Escape") return;
  document.querySelectorAll(".ifx-navbar__menu[open]").forEach((menu) => {
    menu.removeAttribute("open");
  });
});
