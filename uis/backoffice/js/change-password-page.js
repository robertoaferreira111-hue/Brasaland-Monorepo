import {
  changePasswordRequest,
  clearStoredAccessToken,
  getStoredAccessToken,
  resolveApiBase,
  shouldBlockDuplicateSubmit,
  validatePasswordLength,
  validatePasswordMatch,
} from "./auth-api.js";
import { setSubmitting, setupNavigation, showMessage } from "./auth-ui.js";

const apiBase = resolveApiBase();
const form = document.getElementById("change-form");
const submit = document.getElementById("change-submit");
const errorEl = document.getElementById("form-error");
const successEl = document.getElementById("form-success");
const currentError = document.getElementById("current-error");
const passwordError = document.getElementById("password-error");
const confirmError = document.getElementById("confirm-error");

let submitting = false;

setupNavigation();

const accessToken = getStoredAccessToken();
if (!accessToken) {
  window.location.replace("../../login/");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (shouldBlockDuplicateSubmit(submitting)) {
    return;
  }

  showMessage(errorEl, "");
  showMessage(successEl, "");
  showMessage(currentError, "");
  showMessage(passwordError, "");
  showMessage(confirmError, "");

  const currentPassword = form.current_password.value;
  const newPassword = form.new_password.value;
  const confirmation = form.confirm_password.value;

  if (!currentPassword) {
    showMessage(currentError, "Enter your current password.");
    form.current_password.focus();
    return;
  }

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
  setSubmitting(submit, true, "Update password", "Updating…");
  try {
    const result = await changePasswordRequest(apiBase, currentPassword, newPassword, {
      accessToken,
    });
    showMessage(successEl, result.message || "Password has been changed successfully.");
    form.reset();
  } catch (error) {
    const message = error.message || "Unable to change password.";
    if (message === "AUTH_REQUIRED" || /not authenticated|invalid or expired access token/i.test(message)) {
      clearStoredAccessToken();
      window.location.replace("../../login/");
      return;
    }
    showMessage(errorEl, message);
  } finally {
    submitting = false;
    setSubmitting(submit, false, "Update password", "Updating…");
  }
});
