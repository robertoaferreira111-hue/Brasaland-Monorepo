const session = window.BrasalandSession;

session.redirectIfAuthenticated();
document.getElementById("register-link").href = session.appHref("register/");

const form = document.getElementById("login-form");
const formError = document.getElementById("form-error");

function showError(text) {
  formError.hidden = !text;
  formError.textContent = text || "";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  showError("");
  const button = form.querySelector("button");
  button.disabled = true;
  try {
    const response = await session.apiFetch("/auth/login", {
      auth: false,
      method: "POST",
      body: JSON.stringify({
        email: form.email.value,
        password: form.password.value,
      }),
    });
    if (!response.ok) {
      showError(await session.errorText(response));
      return;
    }
    const tokens = await response.json();
    session.saveTokens(tokens.access_token, tokens.refresh_token);
    session.goAfterLogin();
  } catch (_error) {
    showError(`The API is not reachable at ${session.API_BASE}.`);
  } finally {
    button.disabled = false;
  }
});
