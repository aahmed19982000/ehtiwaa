document.addEventListener("DOMContentLoaded", function () {
  initSignupSteps();
  initPasswordStrength();
});

function initSignupSteps() {
  var step1 = document.querySelector("[data-signup-step='1']");
  var step2 = document.querySelector("[data-signup-step='2']");
  var nextBtn = document.querySelector("[data-signup-next]");
  var backBtn = document.querySelector("[data-signup-back]");
  var dot1 = document.querySelector("[data-step-dot='1']");
  var dot2 = document.querySelector("[data-step-dot='2']");
  if (!step1 || !step2 || !nextBtn) return;

  nextBtn.addEventListener("click", function () {
    var requiredFields = step1.querySelectorAll("input[required], select[required]");
    for (var i = 0; i < requiredFields.length; i++) {
      if (!requiredFields[i].reportValidity()) return;
    }
    step1.classList.remove("is-active");
    step2.classList.add("is-active");
    if (dot1) dot1.classList.remove("is-active");
    if (dot2) dot2.classList.add("is-active");
  });

  if (backBtn) {
    backBtn.addEventListener("click", function () {
      step2.classList.remove("is-active");
      step1.classList.add("is-active");
      if (dot2) dot2.classList.remove("is-active");
      if (dot1) dot1.classList.add("is-active");
    });
  }
}

function initPasswordStrength() {
  var input = document.querySelector("[data-password-strength-input]");
  var bar = document.querySelector("[data-password-strength-bar]");
  var label = document.querySelector("[data-password-strength-label]");
  if (!input || !bar || !label) return;

  input.addEventListener("input", function () {
    var score = scorePassword(input.value);
    var percent = Math.min(100, score * 25);
    bar.style.width = percent + "%";

    var levels = ["ضعيفة جدًا", "ضعيفة", "متوسطة", "قوية", "قوية جدًا"];
    var colors = ["#d8352f", "#d8352f", "#ff8a00", "#1e8e5a", "#166b44"];
    var idx = Math.min(levels.length - 1, score);
    label.textContent = input.value ? "قوة كلمة المرور: " + levels[idx] : "";
    bar.style.background = colors[idx];
  });
}

function scorePassword(value) {
  var score = 0;
  if (value.length >= 8) score++;
  if (value.length >= 12) score++;
  if (/[A-Z]/.test(value) && /[a-z]/.test(value)) score++;
  if (/[0-9]/.test(value)) score++;
  if (/[^A-Za-z0-9]/.test(value)) score++;
  return score;
}
