document.addEventListener("DOMContentLoaded", function () {
  var hamburgerBtn = document.querySelector("[data-hamburger-btn]");
  var mobileNav = document.querySelector("[data-mobile-nav]");
  if (!hamburgerBtn || !mobileNav) return;

  hamburgerBtn.addEventListener("click", function () {
    mobileNav.classList.toggle("is-open");
  });
});
