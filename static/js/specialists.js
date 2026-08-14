document.addEventListener("DOMContentLoaded", function () {
  var radios = document.querySelectorAll("[data-category-radio]");
  var groups = document.querySelectorAll("[data-category-group]");
  if (!radios.length || !groups.length) return;

  function showCategory(value) {
    groups.forEach(function (group) {
      var members = group.getAttribute("data-category-group").split(",");
      group.classList.toggle("is-active", members.indexOf(value) !== -1);
    });
  }

  radios.forEach(function (radio) {
    radio.addEventListener("change", function () {
      if (radio.checked) showCategory(radio.value);
    });
    if (radio.checked) showCategory(radio.value);
  });
});
