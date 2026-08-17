document.addEventListener("DOMContentLoaded", function () {
  var tabs = document.querySelectorAll("[data-course-tab]");
  var panels = document.querySelectorAll("[data-course-panel]");
  if (!tabs.length || !panels.length) return;

  function showTab(name) {
    tabs.forEach(function (tab) {
      tab.classList.toggle("is-active", tab.getAttribute("data-course-tab") === name);
    });
    panels.forEach(function (panel) {
      panel.classList.toggle("is-active", panel.getAttribute("data-course-panel") === name);
    });
  }

  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      showTab(tab.getAttribute("data-course-tab"));
    });
  });
});
