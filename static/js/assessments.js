document.addEventListener("DOMContentLoaded", function () {
  var chips = document.querySelectorAll("[data-topic-chip]");
  var cards = document.querySelectorAll("[data-topic-card]");
  if (chips.length && cards.length) {
    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        var topic = chip.getAttribute("data-topic-chip");
        chips.forEach(function (c) {
          c.classList.toggle("is-active", c === chip);
        });
        cards.forEach(function (card) {
          var show = !topic || card.getAttribute("data-topic-card") === topic;
          card.style.display = show ? "" : "none";
        });
      });
    });
  }

  var copyBtn = document.querySelector("[data-copy-link]");
  if (copyBtn) {
    copyBtn.addEventListener("click", function () {
      var url = copyBtn.getAttribute("data-url");
      var originalText = copyBtn.textContent;
      navigator.clipboard.writeText(url).then(function () {
        copyBtn.textContent = copyBtn.getAttribute("data-copied-label") || "تم نسخ الرابط";
        setTimeout(function () {
          copyBtn.textContent = originalText;
        }, 2000);
      });
    });
  }
});
