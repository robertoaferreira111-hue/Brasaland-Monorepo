import {
  getResetTokenFromSearch,
  resolveApiBase,
  resetPasswordRequest,
  shouldBlockDuplicateSubmit,
  validatePasswordLength,
  validatePasswordMatch,
} from "./auth-api.js";
import { setSubmitting, setupNavigation, showMessage } from "./auth-ui.js";

const apiBase = resolveApiBase();
const form = document.getElementById("reset-form");
const submit = document.getElementById("reset-submit");
const errorEl = document.getElementById("form-error");
const successEl = document.getElementById("form-success");
const passwordError = document.getElementById("password-error");
const confirmError = document.getElementById("confirm-error");
const missingTokenPanel = document.getElementById("missing-token");

let submitting = false;
const token = getResetTokenFromSearch(window.location.search);

setupNavigation();

if (!token) {
  form.hidden = true;
  missingTokenPanel.hidden = false;
  showMessage(
    errorEl,
    "This reset link is missing a token. Request a new password reset email.",
  );
} else {
  missingTokenPanel.hidden = true;
  form.hidden = false;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!token || shouldBlockDuplicateSubmit(submitting)) {
    return;
  }

  showMessage(errorEl, "");
  showMessage(successEl, "");
  showMessage(passwordError, "");
  showMessage(confirmError, "");

  const newPassword = form.new_password.value;
  const confirmation = form.confirm_password.value;

  const lengthError = validatePasswordLength(newPassword);
  if (lengthError) {
    showMessage(passwordError, lengthError);
    form.new_password.setAttribute("aria-invalid", "true");
    form.new_password.focus();
    return;
  }
  form.new_password.removeAttribute("aria-invalid");

  const matchError = validatePasswordMatch(newPassword, confirmation);
  if (matchError) {
    showMessage(confirmError, matchError);
    form.confirm_password.setAttribute("aria-invalid", "true");
    form.confirm_password.focus();
    return;
  }
  form.confirm_password.removeAttribute("aria-invalid");

  submitting = true;
  setSubmitting(submit, true, "Reset password", "Resetting…");
  try {
    const result = await resetPasswordRequest(apiBase, token, newPassword);
    showMessage(successEl, result.message || "Password has been reset successfully.");
    form.hidden = true;
    window.setTimeout(() => {
      window.location.assign("../login/");
    }, 1200);
  } catch (error) {
    showMessage(
      errorEl,
      error.message || "Invalid or expired reset token. Request a new reset link.",
    );
  } finally {
    submitting = false;
    setSubmitting(submit, false, "Reset password", "Resetting…");
  }
});
