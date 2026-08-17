document.addEventListener("DOMContentLoaded", function () {
  var tabs = document.querySelector("[data-home-tabs]");
  if (!tabs) return;

  var buttons = tabs.querySelectorAll("[data-tab-btn]");
  var panels = document.querySelectorAll("[data-tab-panel]");

  buttons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var target = btn.getAttribute("data-tab-btn");

      buttons.forEach(function (b) {
        b.classList.toggle("is-active", b === btn);
      });
      panels.forEach(function (panel) {
        panel.hidden = panel.getAttribute("data-tab-panel") !== target;
      });
    });
  });
});
