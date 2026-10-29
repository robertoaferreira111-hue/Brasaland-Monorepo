"use client";

import { resolveApiBase } from "./apiBase";

export const ACCESS_KEY = "brasaland.access_token";
export const REFRESH_KEY = "brasaland.refresh_token";

export const hasAccessToken = () =>
  typeof window !== "undefined" && Boolean(localStorage.getItem(ACCESS_KEY));

export function saveTokens(accessToken: string, refreshToken?: string) {
  localStorage.setItem(ACCESS_KEY, accessToken);
  if (refreshToken) localStorage.setItem(REFRESH_KEY, refreshToken);
}

export function clearSession() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export function appHref(path: string, params?: URLSearchParams) {
  const url = new URL(path, window.location.origin);
  const api = new URLSearchParams(window.location.search).get("api");
  if (api) url.searchParams.set("api", api);
  params?.forEach((value, key) => url.searchParams.set(key, value));
  return `${url.pathname}${url.search}${url.hash}`;
}

export function redirectToLogin() {
  const params = new URLSearchParams();
  const next = `${window.location.pathname}${window.location.search}`;
  if (!next.startsWith("/login")) params.set("next", next);
  window.location.replace(appHref("/login", params));
}

export function goAfterLogin() {
  const next = new URLSearchParams(window.location.search).get("next");
  if (next?.startsWith("/") && !next.startsWith("//") && !next.startsWith("/login")) {
    window.location.replace(next);
  } else {
    window.location.replace(appHref("/"));
  }
}

async function tryRefresh() {
  const refreshToken = localStorage.getItem(REFRESH_KEY);
  if (!refreshToken) return false;
  try {
    const response = await fetch(`${resolveApiBase()}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) return false;
    const data = (await response.json()) as {
      access_token?: string;
      refresh_token?: string;
    };
    if (!data.access_token) return false;
    saveTokens(data.access_token, data.refresh_token || refreshToken);
    return true;
  } catch {
    return false;
  }
}

export async function apiFetch(
  path: string,
  options: RequestInit & { auth?: boolean; retryOnUnauthorized?: boolean } = {},
) {
  const authenticated = options.auth !== false;
  const headers = new Headers(options.headers);
  if (authenticated) {
    const token = localStorage.getItem(ACCESS_KEY);
    if (!token) {
      redirectToLogin();
      throw new Error("Not authenticated");
    }
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const url = path.startsWith("http") ? path : `${resolveApiBase()}${path}`;
  const init = { ...options, headers };
  let response = await fetch(url, init);
  if (response.status === 401 && authenticated && options.retryOnUnauthorized !== false) {
    if (await tryRefresh()) {
      headers.set("Authorization", `Bearer ${localStorage.getItem(ACCESS_KEY)}`);
      response = await fetch(url, { ...init, headers });
    }
    if (response.status === 401) {
      clearSession();
      redirectToLogin();
      throw new Error("Session expired");
    }
  }
  return response;
}

export async function logout() {
  const token = localStorage.getItem(ACCESS_KEY);
  clearSession();
  if (token) {
    try {
      await fetch(`${resolveApiBase()}/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      // The local session is already cleared.
    }
  }
  redirectToLogin();
}

export async function errorText(response: Response) {
  try {
    const payload = (await response.json()) as { detail?: string | { msg?: string }[] };
    if (typeof payload.detail === "string") return payload.detail;
    if (Array.isArray(payload.detail)) {
      return payload.detail.map((item) => item.msg).filter(Boolean).join(" ");
    }
  } catch {
    // Fall through to the status message.
  }
  return `The API returned HTTP ${response.status}.`;
}
