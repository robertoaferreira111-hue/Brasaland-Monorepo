const session = window.BrasalandSession;

session.redirectIfAuthenticated();
if (!session.hasAccessToken() && window.BrasalandTelemetry) {
  try {
    window.BrasalandTelemetry.noteCurrentPage();
  } catch (_telemetryError) {
    // The login form still works.
  }
}
document.getElementById("register-link").href = session.hrefWithApi("../register/");

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
      if (window.BrasalandTelemetry) {
        try {
          window.BrasalandTelemetry.noteLoginFailure(response.status);
        } catch (_telemetryError) {
          // Sign-in still shows the API error.
        }
      }
      showError(await session.errorText(response));
      return;
    }
    const tokens = await response.json();
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
