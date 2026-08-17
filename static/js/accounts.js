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

// Must match AUTH_PASSWORD_VALIDATORS' MinimumLengthValidator (Django) and
// the Auth0 Database connection's password policy — keep all three in sync.
var MIN_PASSWORD_LENGTH = 8;

function initPasswordStrength() {
  var input = document.querySelector("[data-password-strength-input]");
  var bar = document.querySelector("[data-password-strength-bar]");
  var label = document.querySelector("[data-password-strength-label]");
  if (!input || !bar || !label) return;

  input.addEventListener("input", function () {
    var length = input.value.length;
    var percent = Math.min(100, (length / MIN_PASSWORD_LENGTH) * 100);
    bar.style.width = percent + "%";

    if (!input.value) {
      label.textContent = "";
      bar.style.background = "#d8352f";
      return;
    }
    if (length < MIN_PASSWORD_LENGTH) {
      label.textContent = "كلمة المرور قصيرة (" + length + "/" + MIN_PASSWORD_LENGTH + " حرفًا على الأقل)";
      bar.style.background = "#d8352f";
    } else {
      label.textContent = "كلمة المرور تفي بالحد الأدنى للطول";
      bar.style.background = "#1e8e5a";
    }
  });
}
