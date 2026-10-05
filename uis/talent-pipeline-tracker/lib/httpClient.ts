import { ApiError } from "@/types/api";

/**
 * Centralized HTTP client for the Talent Tracker API.
 * All data access must go through this module (via `/services`), not `fetch` in components.
 */

function getBaseUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_URL;
  if (!base) {
    throw new ApiError(
      "API URL is not configured. Set NEXT_PUBLIC_API_URL in .env.local.",
      null,
    );
  }
  return base.replace(/\/$/, "");
}

function messageFromBody(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") return fallback;

  const record = body as Record<string, unknown>;

  if (typeof record.error === "string" && record.error.trim()) {
    return record.error;
  }

  if (typeof record.detail === "string" && record.detail.trim()) {
    return record.detail;
  }

  if (Array.isArray(record.detail)) {
    const parts = record.detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          const msg = (item as { msg?: unknown }).msg;
          return typeof msg === "string" ? msg : null;
        }
        return null;
      })
      .filter((msg): msg is string => Boolean(msg));
    if (parts.length > 0) return parts.join(", ");
  }

  return fallback;
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${getBaseUrl()}${path.startsWith("/") ? path : `/${path}`}`;

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...(options.headers ?? {}),
      },
    });
  } catch (cause) {
    throw new ApiError(
      "Network error while contacting the Talent Tracker API.",
      null,
      cause,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const rawText = await response.text();
  let parsed: unknown = undefined;

  if (rawText) {
    try {
      parsed = JSON.parse(rawText) as unknown;
    } catch (cause) {
      throw new ApiError(
        `Malformed JSON in API response (${response.status}).`,
        response.status,
        cause,
      );
    }
  }

  if (!response.ok) {
    throw new ApiError(
      messageFromBody(
        parsed,
        `Request failed with status ${response.status}.`,
      ),
      response.status,
      parsed,
    );
  }

  return parsed as T;
}
