document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("[data-qty-stepper]").forEach(function (stepper) {
    var input = stepper.querySelector("[data-qty-input]");
    var decrease = stepper.querySelector("[data-qty-decrease]");
    var increase = stepper.querySelector("[data-qty-increase]");
    if (!input) return;

    function clamp(value) {
      var min = input.min !== "" ? parseInt(input.min, 10) : 0;
      var max = input.max !== "" ? parseInt(input.max, 10) : Infinity;
      return Math.min(Math.max(value, min), max);
    }

    if (decrease) {
      decrease.addEventListener("click", function () {
        input.value = clamp((parseInt(input.value, 10) || 0) - 1);
      });
    }
    if (increase) {
      increase.addEventListener("click", function () {
        input.value = clamp((parseInt(input.value, 10) || 0) + 1);
      });
    }
  });

  var gallery = document.querySelector("[data-product-gallery]");
  if (gallery) {
    var mainImg = gallery.querySelector("[data-gallery-main]");
    var thumbs = gallery.querySelectorAll("[data-gallery-thumb]");
    thumbs.forEach(function (thumb) {
      thumb.addEventListener("click", function () {
        if (mainImg) mainImg.src = thumb.getAttribute("data-full");
        thumbs.forEach(function (t) {
          t.classList.toggle("is-active", t === thumb);
        });
      });
    });
  }
});
