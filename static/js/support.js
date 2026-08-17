document.addEventListener("DOMContentLoaded", function () {
  var wrapper = document.querySelector("[data-support-search]");
  if (!wrapper) return;

  var input = wrapper.querySelector("[data-support-search-input]");
  var resultsBox = wrapper.querySelector("[data-support-search-results]");
  var debounceTimer = null;

  function renderNoResults() {
    resultsBox.innerHTML =
      '<div class="support-search__empty">' +
      '<div class="support-search__empty-title">لا توجد نتائج مطابقة</div>' +
      '<div class="support-search__empty-note">جرّب كلمات مختلفة أو أرسل تذكرة دعم وسيتواصل معك فريقنا.</div>' +
      '<a href="#ticket-form" class="btn btn-primary">إرسال تذكرة دعم</a>' +
      "</div>";
    resultsBox.hidden = false;
  }

  function renderResults(results) {
    resultsBox.innerHTML = results
      .map(function (r) {
        return '<a href="#faq-' + r.id + '" class="support-search__result" data-faq-id="' + r.id + '">' + r.question + "</a>";
      })
      .join("");
    resultsBox.hidden = false;
  }

  function runSearch(query) {
    fetch("/support/search/?q=" + encodeURIComponent(query))
      .then(function (response) {
        return response.json();
      })
      .then(function (data) {
        if (!data.results.length) {
          renderNoResults();
        } else {
          renderResults(data.results);
        }
      });
  }

  input.addEventListener("input", function () {
    var query = input.value.trim();
    clearTimeout(debounceTimer);
    if (!query) {
      resultsBox.hidden = true;
      resultsBox.innerHTML = "";
      return;
    }
    debounceTimer = setTimeout(function () {
      runSearch(query);
    }, 250);
  });

  resultsBox.addEventListener("click", function (event) {
    var link = event.target.closest("[data-faq-id]");
    if (!link) return;
    var target = document.getElementById("faq-" + link.getAttribute("data-faq-id"));
    if (target) {
      event.preventDefault();
      target.setAttribute("open", "");
      target.scrollIntoView({ behavior: "smooth", block: "center" });
      resultsBox.hidden = true;
    }
  });

  document.addEventListener("click", function (event) {
    if (!wrapper.contains(event.target)) {
      resultsBox.hidden = true;
    }
  });
});
