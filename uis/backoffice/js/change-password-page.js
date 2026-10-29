const session = window.BrasalandSession;
const MIN_PASSWORD_LENGTH = 8;

session.requireSession();

document.getElementById("directory-link").href = session.appHref("index.html");
document.getElementById("account-link").href = session.appHref("account/profile/");
document.getElementById("logout").addEventListener("click", () => {
  session.logout();
});

const toggle = document.getElementById("nav-toggle");
const nav = document.getElementById("site-nav");
toggle.addEventListener("click", () => {
  const open = nav.classList.toggle("is-open");
  toggle.setAttribute("aria-expanded", String(open));
  toggle.textContent = open ? "Close navigation" : "Open navigation";
});

const form = document.getElementById("change-form");
const formError = document.getElementById("form-error");
const formSuccess = document.getElementById("form-success");
const currentError = document.getElementById("current-error");
const passwordError = document.getElementById("password-error");
const confirmError = document.getElementById("confirm-error");

function showMessage(element, text) {
  element.hidden = !text;
  element.textContent = text || "";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  showMessage(formError, "");
  showMessage(formSuccess, "");
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

  const button = document.getElementById("change-submit");
  button.disabled = true;
  try {
    const response = await session.apiFetch("/auth/change-password", {
      method: "POST",
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });
    if (!response.ok) {
      showMessage(formError, await session.errorText(response));
      return;
    }
    const body = await response.json();
    showMessage(
      formSuccess,
      body.message || "Password has been changed successfully.",
    );
    form.reset();
  } catch (error) {
    if (error instanceof Error && error.message === "Session expired") {
      return;
    }
    showMessage(formError, `The API is not reachable at ${session.API_BASE}.`);
  } finally {
    button.disabled = false;
  }
});
