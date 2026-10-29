const session = window.BrasalandSession;
const MIN_PASSWORD_LENGTH = 8;

document.getElementById("login-link").href = session.appHref("login/");
document.getElementById("forgot-link").href = session.appHref("forgot-password/");
document.getElementById("forgot-link-missing").href =
  session.appHref("forgot-password/");

const form = document.getElementById("reset-form");
const formError = document.getElementById("form-error");
const formSuccess = document.getElementById("form-success");
const passwordError = document.getElementById("password-error");
const confirmError = document.getElementById("confirm-error");
const missingTokenPanel = document.getElementById("missing-token");
const token = new URLSearchParams(window.location.search).get("token") || "";

function showMessage(element, text) {
  element.hidden = !text;
  element.textContent = text || "";
}

if (!token) {
  form.hidden = true;
  missingTokenPanel.hidden = false;
  showMessage(
    formError,
    "This reset link is missing a token. Request a new password reset email.",
  );
} else {
  missingTokenPanel.hidden = true;
  form.hidden = false;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!token) {
    return;
  }
  showMessage(formError, "");
  showMessage(formSuccess, "");
  showMessage(passwordError, "");
  showMessage(confirmError, "");

  const newPassword = form.new_password.value;
  const confirmation = form.confirm_password.value;
  if (newPassword.length < MIN_PASSWORD_LENGTH) {
    showMessage(
      passwordError,
      `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`,
    );
    form.new_password.focus();
    return;
  }
  if (newPassword !== confirmation) {
    showMessage(confirmError, "New password and confirmation must match.");
    form.confirm_password.focus();
    return;
  }

  const button = document.getElementById("reset-submit");
  button.disabled = true;
  try {
    const response = await session.apiFetch("/auth/reset-password", {
      auth: false,
      method: "POST",
      body: JSON.stringify({ token, new_password: newPassword }),
    });
    if (!response.ok) {
      showMessage(formError, await session.errorText(response));
      return;
    }
    const body = await response.json();
    showMessage(
      formSuccess,
      body.message || "Password has been reset successfully.",
    );
    form.hidden = true;
    window.setTimeout(() => {
      window.location.assign(session.appHref("login/"));
    }, 1200);
  } catch (_error) {
    showMessage(formError, `The API is not reachable at ${session.API_BASE}.`);
  } finally {
    button.disabled = false;
  }
});
