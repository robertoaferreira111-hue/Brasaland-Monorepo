function resolveApiBase() {
  const override = new URLSearchParams(window.location.search).get("api");
  if (override) {
    return override.replace(/\/+$/, "");
  }
  const { hostname, protocol } = window.location;
  if (hostname.endsWith(".app.github.dev")) {
    const apiHost = hostname.replace(/-\d+(?=\.app\.github\.dev$)/, "-8000");
    return `${protocol}//${apiHost}`;
  }
  // Local docker/desktop defaults
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return "http://127.0.0.1:8000";
  }
  // Same-host production / VPS: UIs on :3000|:3001, API published on :8000
  return `${protocol}//${hostname}:8000`;
}

const API_BASE = resolveApiBase();
const ACCESS_KEY = "brasaland.access_token";
const REFRESH_KEY = "brasaland.refresh_token";

function readAccess() {
  return localStorage.getItem(ACCESS_KEY) || "";
}

function readRefresh() {
  return localStorage.getItem(REFRESH_KEY) || "";
}

function hasAccessToken() {
  return Boolean(readAccess());
}

function saveTokens(accessToken, refreshToken) {
  localStorage.setItem(ACCESS_KEY, accessToken);
  if (refreshToken) {
    localStorage.setItem(REFRESH_KEY, refreshToken);
  }
}

function clearSession() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

function currentQuery() {
  return new URLSearchParams(window.location.search);
}

function hrefWithApi(path) {
  const api = currentQuery().get("api");
  if (!api) {
    return path;
  }
  const join = path.includes("?") ? "&" : "?";
  return `${path}${join}api=${encodeURIComponent(api)}`;
}

function redirectToLogin() {
  const params = new URLSearchParams();
  const api = currentQuery().get("api");
  if (api) {
    params.set("api", api);
  }
  const next = `${window.location.pathname}${window.location.search}`;
  if (!next.startsWith("/login")) {
    params.set("next", next);
  }
  const query = params.toString();
  window.location.replace(query ? `/login/?${query}` : "/login/");
}

function goAfterLogin() {
  const next = currentQuery().get("next");
  if (
    next &&
    next.startsWith("/") &&
    !next.startsWith("//") &&
    !next.startsWith("/login")
  ) {
    window.location.replace(next);
    return;
  }
  window.location.replace(hrefWithApi("/"));
}

function requireSession() {
  if (!hasAccessToken()) {
    redirectToLogin();
  }
}

function redirectIfAuthenticated() {
  if (hasAccessToken()) {
    goAfterLogin();
  }
}

async function tryRefresh() {
  const refresh = readRefresh();
  if (!refresh) {
    return false;
  }
  let response;
  try {
    response = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
  } catch (_error) {
    return false;
  }
  if (!response.ok) {
    return false;
  }
  let data;
  try {
    data = await response.json();
  } catch (_error) {
    return false;
  }
  if (!data.access_token) {
    return false;
  }
  saveTokens(data.access_token, data.refresh_token || refresh);
  return true;
}

async function apiFetch(path, options = {}) {
  const authenticated = options.auth !== false;
  const retryOnUnauthorized = options.retryOnUnauthorized !== false;
  const requestHeaders = new Headers(options.headers || {});
  if (authenticated) {
    if (!readAccess()) {
      redirectToLogin();
      throw new Error("Not authenticated");
    }
    requestHeaders.set("Authorization", `Bearer ${readAccess()}`);
  }
  if (options.body && !requestHeaders.has("Content-Type")) {
    requestHeaders.set("Content-Type", "application/json");
  }
  const url = String(path).startsWith("http") ? path : `${API_BASE}${path}`;
  let response = await fetch(url, {
    method: options.method,
    body: options.body,
    headers: requestHeaders,
  });
  if (response.status === 401 && authenticated && retryOnUnauthorized) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      requestHeaders.set("Authorization", `Bearer ${readAccess()}`);
      response = await fetch(url, {
        method: options.method,
        body: options.body,
        headers: requestHeaders,
      });
    }
    if (response.status === 401) {
      clearSession();
      redirectToLogin();
      throw new Error("Session expired");
    }
  }
  return response;
}

async function logout() {
  const token = readAccess();
  clearSession();
  if (token) {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch (_error) {
      // Local session is already cleared. The login page is the next step.
    }
  }
  redirectToLogin();
}

async function errorText(response) {
  try {
    const payload = await response.json();
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (Array.isArray(payload.detail)) {
      return payload.detail
        .map((item) => item.msg)
        .filter(Boolean)
        .join(" ");
    }
  } catch (_error) {
    return `The API returned HTTP ${response.status}.`;
  }
  return `The API returned HTTP ${response.status}.`;
}

window.BrasalandSession = {
  API_BASE,
  hasAccessToken,
  saveTokens,
  clearSession,
  hrefWithApi,
  requireSession,
  redirectIfAuthenticated,
  apiFetch,
  logout,
  errorText,
  goAfterLogin,
};
