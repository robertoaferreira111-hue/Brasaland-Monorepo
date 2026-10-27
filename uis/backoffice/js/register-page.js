const session = window.BrasalandSession;

session.redirectIfAuthenticated();
document.getElementById("login-link").href = session.hrefWithApi("../login/");

const form = document.getElementById("register-form");
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
  const email = form.email.value;
  const password = form.password.value;
  try {
    const created = await session.apiFetch("/users", {
      auth: false,
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (!created.ok) {
      showError(await session.errorText(created));
      return;
    }
    const login = await session.apiFetch("/auth/login", {
      auth: false,
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (!login.ok) {
      if (window.BrasalandTelemetry) {
        try {
          window.BrasalandTelemetry.noteLoginFailure(login.status);
        } catch (_telemetryError) {
          // Registration still shows the API error.
        }
      }
      showError(await session.errorText(login));
      return;
    }
    const tokens = await login.json();
    session.saveTokens(tokens.access_token, tokens.refresh_token);
    if (window.BrasalandTelemetry) {
      try {
        window.BrasalandTelemetry.noteLoginSuccess();
      } catch (_telemetryError) {
        // The session is already stored.
      }
    }
    session.goAfterLogin();
  } catch (_error) {
    showError(`The API is not reachable at ${session.API_BASE}.`);
  } finally {
    button.disabled = false;
  }
});
