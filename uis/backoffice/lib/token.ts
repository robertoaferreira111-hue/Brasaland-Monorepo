const ACCESS_KEY = "brasaland_access_token";
const REFRESH_KEY = "brasaland_refresh_token";

export type TokenStore = Pick<Storage, "getItem" | "setItem" | "removeItem">;

function present(value: string | null | undefined): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function browserStore(): TokenStore | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage;
}

export function readAccessToken(store: TokenStore): string | null {
  return present(store.getItem(ACCESS_KEY));
}

export function readRefreshToken(store: TokenStore): string | null {
  return present(store.getItem(REFRESH_KEY));
}

export function hasAccessTokenIn(store: TokenStore): boolean {
  return readAccessToken(store) !== null;
}

export function writeSession(
  store: TokenStore,
  access: string,
  refresh: string | null,
): void {
  const accessToken = present(access);
  if (!accessToken) {
    return;
  }
  store.setItem(ACCESS_KEY, accessToken);
  const refreshToken = present(refresh);
  if (refreshToken) {
    store.setItem(REFRESH_KEY, refreshToken);
  } else {
    store.removeItem(REFRESH_KEY);
  }
}

export function clearSession(store: TokenStore): void {
  store.removeItem(ACCESS_KEY);
  store.removeItem(REFRESH_KEY);
}

export function authorizationValue(token: string): string {
  return `Bearer ${token}`;
}

export function getAccessToken(): string | null {
  const store = browserStore();
  return store ? readAccessToken(store) : null;
}

export function getRefreshToken(): string | null {
  const store = browserStore();
  return store ? readRefreshToken(store) : null;
}

export function hasAccessToken(): boolean {
  const store = browserStore();
  return store ? hasAccessTokenIn(store) : false;
}

export function setTokens(access: string, refresh: string | null): void {
  const store = browserStore();
  if (!store) {
    return;
  }
  writeSession(store, access, refresh);
}

export function clearTokens(): void {
  const store = browserStore();
  if (!store) {
    return;
  }
  clearSession(store);
}

export function readSessionTokens(
  data: unknown,
): { access: string; refresh: string | null } | null {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    return null;
  }
  const body = data as Record<string, unknown>;
  const access = [body.access_token, body.token, body.accessToken]
    .map((value) => (typeof value === "string" ? value : null))
    .map((value) => present(value))
    .find((value) => value !== null && value !== undefined);
  if (!access) {
    return null;
  }
  const refreshCandidate = body.refresh_token ?? body.refreshToken;
  const refresh = present(
    typeof refreshCandidate === "string" ? refreshCandidate : null,
  );
  return { access, refresh };
}

export function sessionClearedOnUnauthorized(
  status: number,
  refreshed: boolean,
): boolean {
  return status === 401 && !refreshed;
}

export const SESSION_EXPIRED_EVENT = "brasaland:session-expired";

let endingSession = false;

export function resetSessionLifecycleForTests(): void {
  endingSession = false;
}

export function notifySessionExpired(): void {
  if (typeof window === "undefined") {
    return;
  }
  if (window.location.pathname === "/login") {
    return;
  }
  window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
}

/**
 * Clears the stored JWT and asks the app to open /login.
 * Repeated calls during the same expiry do not fire extra redirects.
 */
export function invalidateSession(): void {
  clearTokens();
  if (endingSession) {
    return;
  }
  endingSession = true;
  try {
    notifySessionExpired();
  } finally {
    queueMicrotask(() => {
      endingSession = false;
    });
  }
}

export function sessionStillActive(): boolean {
  return hasAccessToken() && Boolean(getAccessToken());
}
