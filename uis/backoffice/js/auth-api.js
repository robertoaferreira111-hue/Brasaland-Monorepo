/**
 * Auth API client and pure helpers for Brasaland backoffice.
 * Keep token values out of logs and user-visible error strings.
 */

export const TOKEN_STORAGE_KEY = "brasaland_access_token";
export const MIN_PASSWORD_LENGTH = 8;

export const FORGOT_CONFIRMATION_MESSAGE =
  "If that address is registered, you'll receive a link shortly.";

export function resolveApiBase(locationLike = globalThis.location) {
  const search = locationLike?.search ?? "";
  const override = new URLSearchParams(search).get("api");
  if (override) {
    return override.replace(/\/+$/, "");
  }
  const hostname = locationLike?.hostname ?? "";
  const protocol = locationLike?.protocol ?? "http:";
  if (hostname.endsWith(".app.github.dev")) {
    const apiHost = hostname.replace(/-\d+(?=\.app\.github\.dev$)/, "-8000");
    return `${protocol}//${apiHost}`;
  }
  return "http://127.0.0.1:8000";
}

export function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email ?? "").trim());
}

export function validatePasswordLength(password, minLength = MIN_PASSWORD_LENGTH) {
  const value = String(password ?? "");
  if (value.length < minLength) {
    return `Password must be at least ${minLength} characters.`;
  }
  return "";
}

export function validatePasswordMatch(password, confirmation) {
  if (String(password ?? "") !== String(confirmation ?? "")) {
    return "New password and confirmation must match.";
  }
  return "";
}

export function buildForgotPasswordPayload(email) {
  return { email: String(email ?? "").trim().toLowerCase() };
}

export function buildResetPasswordPayload(token, newPassword) {
  return {
    token: String(token ?? ""),
    new_password: String(newPassword ?? ""),
  };
}

export function buildChangePasswordPayload(currentPassword, newPassword) {
  return {
    current_password: String(currentPassword ?? ""),
    new_password: String(newPassword ?? ""),
  };
}

export function buildLoginPayload(email, password) {
  return {
    email: String(email ?? "").trim().toLowerCase(),
    password: String(password ?? ""),
  };
}

export function getResetTokenFromSearch(search) {
  const params = new URLSearchParams(
    typeof search === "string" ? search : search?.toString?.() ?? "",
  );
  return params.get("token") ?? "";
}

export function shouldBlockDuplicateSubmit(isSubmitting) {
  return Boolean(isSubmitting);
}

export function createAuthHeaders(accessToken) {
  const headers = { "Content-Type": "application/json" };
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }
  return headers;
}

export async function readApiError(response) {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") {
      return body.detail;
    }
    if (Array.isArray(body?.detail)) {
      return body.detail.map((item) => item.msg || String(item)).join(" ");
    }
    if (typeof body?.message === "string") {
      return body.message;
    }
  } catch {
    /* ignore non-JSON */
  }
  return `Request failed (${response.status}).`;
}

export function getStoredAccessToken(storage = globalThis.localStorage) {
  try {
    return storage?.getItem(TOKEN_STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
}

export function setStoredAccessToken(token, storage = globalThis.localStorage) {
  storage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearStoredAccessToken(storage = globalThis.localStorage) {
  storage.removeItem(TOKEN_STORAGE_KEY);
}

export function requireAccessToken(storage = globalThis.localStorage) {
  const token = getStoredAccessToken(storage);
  if (!token) {
    throw new Error("AUTH_REQUIRED");
  }
  return token;
}

async function postJson(apiBase, path, payload, { accessToken, fetchImpl } = {}) {
  const fetchFn = fetchImpl ?? globalThis.fetch;
  const response = await fetchFn(`${apiBase}${path}`, {
    method: "POST",
    headers: createAuthHeaders(accessToken),
    body: JSON.stringify(payload),
  });
  return response;
}

export async function loginRequest(apiBase, email, password, options = {}) {
  const payload = buildLoginPayload(email, password);
  const response = await postJson(apiBase, "/auth/login", payload, options);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return response.json();
}

export async function forgotPasswordRequest(apiBase, email, options = {}) {
  const payload = buildForgotPasswordPayload(email);
  const response = await postJson(apiBase, "/auth/forgot-password", payload, options);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  const body = await response.json();
  return {
    message: body.message || FORGOT_CONFIRMATION_MESSAGE,
    payload,
  };
}

export async function resetPasswordRequest(apiBase, token, newPassword, options = {}) {
  const payload = buildResetPasswordPayload(token, newPassword);
  const response = await postJson(apiBase, "/auth/reset-password", payload, options);
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return response.json();
}

export async function changePasswordRequest(
  apiBase,
  currentPassword,
  newPassword,
  options = {},
) {
  const accessToken = options.accessToken ?? requireAccessToken(options.storage);
  const payload = buildChangePasswordPayload(currentPassword, newPassword);
  const response = await postJson(apiBase, "/auth/change-password", payload, {
    ...options,
    accessToken,
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return response.json();
}
