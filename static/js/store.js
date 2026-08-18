document.addEventListener("DOMContentLoaded", function () {
  // Matches the "1234,56 ج.م" formatting the server renders (Arabic
  // locale decimal comma) — keeps the live preview visually identical to
  // what a page reload would show, so it doesn't look like a different,
  // wrong number.
  function formatPrice(amount) {
    return amount.toFixed(2).replace(".", ",");
  }

  function recalcCartTotals() {
    var subtotalEl = document.querySelector("[data-cart-subtotal]");
    var subtotal = 0;
    document.querySelectorAll("[data-cart-row]").forEach(function (row) {
      var unitPrice = parseFloat(row.getAttribute("data-unit-price")) || 0;
      var qtyInput = row.querySelector("[data-qty-input]");
      var quantity = qtyInput ? parseInt(qtyInput.value, 10) || 0 : 0;
      var lineTotal = unitPrice * quantity;
      subtotal += lineTotal;

      var lineTotalEl = row.querySelector("[data-line-total]");
      if (lineTotalEl) {
        lineTotalEl.textContent = formatPrice(lineTotal) + " ج.م";
      }
    });
    if (subtotalEl) {
      subtotalEl.textContent = formatPrice(subtotal) + " ج.م";
    }
  }

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
        recalcCartTotals();
      });
    }
    if (increase) {
      increase.addEventListener("click", function () {
        input.value = clamp((parseInt(input.value, 10) || 0) + 1);
        recalcCartTotals();
      });
    }
    input.addEventListener("input", recalcCartTotals);
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
