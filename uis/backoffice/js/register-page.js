const session = window.BrasalandSession;

session.redirectIfAuthenticated();
document.getElementById("login-link").href = session.appHref("login/");

const form = document.getElementById("register-form");
const formError = document.getElementById("form-error");
const FIELD_NAMES = ["email", "password", "name", "phone", "address"];

function showFormError(text) {
  formError.hidden = !text;
  formError.textContent = text || "";
}

function showFieldError(name, text) {
  const slot = document.getElementById(`${name}-error`);
  if (!slot) {
    return;
  }
  slot.hidden = !text;
  slot.textContent = text || "";
}

function clearErrors() {
  showFormError("");
  for (const name of FIELD_NAMES) {
    showFieldError(name, "");
  }
}

function clientFieldErrors() {
  const errors = {};
  const email = form.email.value.trim();
  if (!email) {
    errors.email = "Email is required.";
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    errors.email = "Enter a valid email (example: name@email.com).";
  }
  if (!form.password.value) {
    errors.password = "Password is required.";
  }
  return errors;
}

function applyFieldErrors(errors) {
  let shown = false;
  for (const name of FIELD_NAMES) {
    if (!errors[name]) {
      continue;
    }
    showFieldError(name, errors[name]);
    shown = true;
  }
  return shown;
}

async function readPayload(response) {
  try {
    return await response.json();
  } catch (_error) {
    return null;
  }
}

function fieldErrorsFrom(payload) {
  if (!payload || !Array.isArray(payload.detail)) {
    return {};
  }
  const errors = {};
  for (const item of payload.detail) {
    const location = Array.isArray(item.loc)
      ? item.loc.filter((part) => part !== "body")
      : [];
    const field = location[0];
    if (typeof field === "string" && item.msg) {
      errors[field] = item.msg;
    }
  }
  return errors;
}

function messageFrom(payload, status) {
  if (payload && typeof payload.detail === "string") {
    return payload.detail;
  }
  if (payload && Array.isArray(payload.detail)) {
    return payload.detail
      .map((item) => item.msg)
      .filter(Boolean)
      .join(" ");
  }
  return `The API returned HTTP ${status}.`;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearErrors();
  const fieldErrors = clientFieldErrors();
  if (applyFieldErrors(fieldErrors)) {
    return;
  }

  const button = form.querySelector("button");
  button.disabled = true;
  const email = form.email.value.trim();
  const password = form.password.value;
  const profile = {
    name: form.name.value.trim(),
    phone: form.phone.value.trim(),
    address: form.address.value.trim(),
  };
  try {
    const created = await session.apiFetch("/users", {
      auth: false,
      method: "POST",
      body: JSON.stringify({ email, password, ...profile }),
    });
    if (!created.ok) {
      const payload = await readPayload(created);
      if (applyFieldErrors(fieldErrorsFrom(payload))) {
        return;
      }
      showFormError(messageFrom(payload, created.status));
      return;
    }
    const login = await session.apiFetch("/auth/login", {
      auth: false,
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (!login.ok) {
      showFormError(await session.errorText(login));
      return;
    }
    const tokens = await login.json();
    session.saveTokens(tokens.access_token, tokens.refresh_token);
    session.goAfterLogin();
  } catch (_error) {
    showFormError(`The API is not reachable at ${session.API_BASE}.`);
  } finally {
    button.disabled = false;
  }
});
