import {
  FORGOT_CONFIRMATION_MESSAGE,
  forgotPasswordRequest,
  isValidEmail,
  resolveApiBase,
  shouldBlockDuplicateSubmit,
} from "./auth-api.js";
import { setSubmitting, setupNavigation, showMessage } from "./auth-ui.js";

const apiBase = resolveApiBase();
const form = document.getElementById("forgot-form");
const submit = document.getElementById("forgot-submit");
const errorEl = document.getElementById("form-error");
const successEl = document.getElementById("form-success");
const emailError = document.getElementById("email-error");

let submitting = false;

setupNavigation();

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (shouldBlockDuplicateSubmit(submitting)) {
    return;
  }

  showMessage(errorEl, "");
  showMessage(successEl, "");
  showMessage(emailError, "");

  const email = form.email.value;
  if (!isValidEmail(email)) {
    showMessage(emailError, "Enter a valid email (example: name@email.com)");
    form.email.setAttribute("aria-invalid", "true");
    form.email.focus();
    return;
  }
  form.email.removeAttribute("aria-invalid");

  submitting = true;
  setSubmitting(submit, true, "Send reset link", "Sending…");
  try {
    const result = await forgotPasswordRequest(apiBase, email);
    // Always show the same confirmation copy (anti-enumeration).
    showMessage(successEl, result.message || FORGOT_CONFIRMATION_MESSAGE);
    form.reset();
  } catch (error) {
    showMessage(errorEl, error.message || "Unable to send reset link.");
  } finally {
    submitting = false;
    setSubmitting(submit, false, "Send reset link", "Sending…");
  }
});
