import { publicErrorText } from "@/lib/errors";
import { LOGIN_PATH, USERS_PATH } from "@/lib/credentials";
import {
  mergeSavedProfile,
  readProfile,
  type Profile,
} from "@/lib/profile";
import {
  authorizationValue,
  getAccessToken,
  getRefreshToken,
  invalidateSession,
  readSessionTokens,
  SESSION_EXPIRED_EVENT,
  sessionClearedOnUnauthorized,
  setTokens,
} from "@/lib/token";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export type { Profile };
export { readProfile };
export { SESSION_EXPIRED_EVENT };

export class SessionExpiredError extends Error {
  constructor() {
    super("Session expired");
    this.name = "SessionExpiredError";
  }
}

type ApiOptions = RequestInit & {
  auth?: boolean;
  retryOnUnauthorized?: boolean;
};

let refreshInFlight: Promise<boolean> | null = null;

async function errorMessage(response: Response): Promise<string> {
  return publicErrorText(response.status, await response.text());
}

export function toErrorMessage(error: unknown): string {
  if (error instanceof SessionExpiredError) {
    return "";
  }
  if (error instanceof TypeError) {
    return "Could not reach the Brasaland API. Check that it is running.";
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Something went wrong.";
}

async function tryRefresh(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) {
    return false;
  }
  let response: Response;
  try {
    response = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
  } catch {
    return false;
  }
  if (!response.ok) {
    return false;
  }
  let data: unknown;
  try {
    data = await response.json();
  } catch {
    return false;
  }
  const tokens = readSessionTokens(data);
  if (!tokens) {
    return false;
  }
  setTokens(tokens.access, tokens.refresh ?? refresh);
  return true;
}

function refreshOnce(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = tryRefresh().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

function endSession(): never {
  invalidateSession();
  throw new SessionExpiredError();
}

export async function apiFetch(
  path: string,
  options: ApiOptions = {},
): Promise<Response> {
  const { auth = false, retryOnUnauthorized = true, headers, ...rest } =
    options;
  const requestHeaders = new Headers(headers);

  if (auth) {
    const token = getAccessToken();
    if (!token) {
      endSession();
    }
    requestHeaders.set("Authorization", authorizationValue(token));
  }

  if (
    rest.body &&
    !(rest.body instanceof FormData) &&
    !requestHeaders.has("Content-Type")
  ) {
    requestHeaders.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...rest,
    headers: requestHeaders,
  });

  if (response.status === 401 && auth) {
    const refreshed = retryOnUnauthorized && (await refreshOnce());
    if (refreshed) {
      return apiFetch(path, { ...options, retryOnUnauthorized: false });
    }
    if (sessionClearedOnUnauthorized(response.status, refreshed)) {
      endSession();
    }
  }

  return response;
}

export async function login(email: string, password: string): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${LOGIN_PATH}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new TypeError("Could not reach the Brasaland API. Check that it is running.");
    }
    throw error;
  }
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  let data: unknown;
  try {
    data = await response.json();
  } catch {
    throw new Error("Login response did not include a token.");
  }
  const tokens = readSessionTokens(data);
  if (!tokens) {
    throw new Error("Login response did not include a token.");
  }
  setTokens(tokens.access, tokens.refresh);
}

export async function registerUser(input: {
  email: string;
  password: string;
}): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${USERS_PATH}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: input.email,
        password: input.password,
      }),
    });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new TypeError("Could not reach the Brasaland API. Check that it is running.");
    }
    throw error;
  }
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  await login(input.email, input.password);
}

export async function getMe(): Promise<Profile> {
  const response = await apiFetch("/auth/me", { method: "GET", auth: true });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return readProfile(await response.json());
}

export async function updateProfile(
  input: {
    name: string;
    phone: string;
    address: string;
  },
  previousEmail = "",
): Promise<Profile> {
  const response = await apiFetch("/profiles/me", {
    method: "PUT",
    auth: true,
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  if (response.status === 204) {
    return { email: previousEmail, ...input };
  }
  try {
    return mergeSavedProfile(
      readProfile(await response.json()),
      input,
      previousEmail,
    );
  } catch {
    return { email: previousEmail, ...input };
  }
}

export async function logout(): Promise<void> {
  const token = getAccessToken();
  if (token) {
    try {
      await fetch(`${API_URL}/auth/logout`, {
        method: "POST",
        headers: { Authorization: authorizationValue(token) },
        signal: AbortSignal.timeout(4000),
      });
    } catch {
      // The local session still ends if the API is unreachable.
    }
  }
  invalidateSession();
}
