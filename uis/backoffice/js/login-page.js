import {
  isValidEmail,
  loginRequest,
  resolveApiBase,
  setStoredAccessToken,
  shouldBlockDuplicateSubmit,
} from "./auth-api.js";
import { setSubmitting, setupNavigation, showMessage } from "./auth-ui.js";

const apiBase = resolveApiBase();
const form = document.getElementById("login-form");
const submit = document.getElementById("login-submit");
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
  const password = form.password.value;

  if (!isValidEmail(email)) {
    showMessage(emailError, "Enter a valid email (example: name@email.com)");
    form.email.setAttribute("aria-invalid", "true");
    form.email.focus();
    return;
  }
  form.email.removeAttribute("aria-invalid");

  if (!password) {
    showMessage(errorEl, "Enter your password.");
    form.password.focus();
    return;
  }

  submitting = true;
  setSubmitting(submit, true, "Sign in", "Signing in…");
  try {
    const result = await loginRequest(apiBase, email, password);
    setStoredAccessToken(result.access_token);
    showMessage(successEl, "Signed in. Redirecting…");
    window.location.assign("../account/change-password/");
  } catch (error) {
    showMessage(errorEl, error.message || "Unable to sign in.");
  } finally {
    submitting = false;
    setSubmitting(submit, false, "Sign in", "Signing in…");
  }
});
