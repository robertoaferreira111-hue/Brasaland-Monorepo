const session = window.BrasalandSession;
const FORGOT_CONFIRMATION_MESSAGE =
  "If that address is registered, you'll receive a link shortly.";

document.getElementById("login-link").href = session.appHref("login/");

const form = document.getElementById("forgot-form");
const formError = document.getElementById("form-error");
const formSuccess = document.getElementById("form-success");

function showMessage(element, text) {
  element.hidden = !text;
  element.textContent = text || "";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  showMessage(formError, "");
  showMessage(formSuccess, "");
  const button = document.getElementById("forgot-submit");
  button.disabled = true;
  try {
    const response = await session.apiFetch("/auth/forgot-password", {
      auth: false,
      method: "POST",
      body: JSON.stringify({ email: form.email.value }),
    });
    if (!response.ok) {
      showMessage(formError, await session.errorText(response));
      return;
    }
    const body = await response.json();
    showMessage(formSuccess, body.message || FORGOT_CONFIRMATION_MESSAGE);
    form.reset();
  } catch (_error) {
    showMessage(formError, `The API is not reachable at ${session.API_BASE}.`);
  } finally {
    button.disabled = false;
  }
});
