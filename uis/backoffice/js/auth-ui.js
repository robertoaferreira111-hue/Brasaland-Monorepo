/** Shared UI helpers for auth pages. */

export function setupNavigation() {
  const toggle = document.getElementById("nav-toggle");
  const nav = document.getElementById("site-nav");
  if (!toggle || !nav) {
    return;
  }
  toggle.addEventListener("click", () => {
    const open = nav.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", String(open));
    toggle.textContent = open ? "Close navigation" : "Open navigation";
  });
}

export function showMessage(element, text) {
  if (!element) {
    return;
  }
  if (!text) {
    element.hidden = true;
    element.textContent = "";
    return;
  }
  element.hidden = false;
  element.textContent = text;
}

export function setSubmitting(button, isSubmitting, idleLabel, busyLabel) {
  if (!button) {
    return;
  }
  button.disabled = Boolean(isSubmitting);
  if (busyLabel && idleLabel) {
    button.textContent = isSubmitting ? busyLabel : idleLabel;
  }
}

export function focusFirstInvalid(form) {
  const invalid = form.querySelector(":invalid, [aria-invalid='true']");
  if (invalid && typeof invalid.focus === "function") {
    invalid.focus();
  }
}
