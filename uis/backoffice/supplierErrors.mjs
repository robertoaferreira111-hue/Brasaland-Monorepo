/** User-facing copy and safe parsing helpers for the supplier backoffice. */

export const USER_MESSAGES = {
  network:
    "We could not reach the supplier service. Check your connection, then try again. If this keeps happening, contact support.",
  httpGeneric:
    "We could not complete that request. Try again. If the problem continues, contact support.",
  httpNotFound:
    "That supplier was not found. Refresh the list and try again, or contact support.",
  httpInvalid:
    "Some of the submitted values are invalid. Check the highlighted fields and try again.",
  httpServer:
    "The supplier service had a problem. Try again in a moment. If it continues, contact support.",
  storageUnavailable:
    "The supplier database is temporarily unavailable. Try again. If this continues, contact support.",
  storedDataInvalid:
    "That supplier record is damaged and cannot be shown. Try again later, or contact support.",
  unexpectedServer:
    "Something went wrong on the server. Try again. If this continues, contact support.",
  malformed:
    "The supplier service returned an unexpected response. Try again, or contact support.",
  invalidList:
    "The supplier list was incomplete or invalid. Try again, or contact support.",
};

/** Stable FastAPI `{detail}` strings from services/api/app/errors.py */
export const BACKEND_SAFE_DETAILS = {
  storageUnavailable: "Storage unavailable",
  storedDataInvalid: "Stored supplier data is invalid",
  unexpectedError: "An unexpected error occurred",
  notFound: "Supplier not found",
};

const BACKEND_DETAIL_TO_USER = {
  [BACKEND_SAFE_DETAILS.storageUnavailable]: USER_MESSAGES.storageUnavailable,
  [BACKEND_SAFE_DETAILS.storedDataInvalid]: USER_MESSAGES.storedDataInvalid,
  [BACKEND_SAFE_DETAILS.unexpectedError]: USER_MESSAGES.unexpectedServer,
  [BACKEND_SAFE_DETAILS.notFound]: USER_MESSAGES.httpNotFound,
};

const SENSITIVE_DETAIL =
  /traceback|file\s+"|\/users\/|\/home\/|\\|password\s*=|secret|api[_-]?key|suppliers\.json/i;

/**
 * Map a FastAPI-style error payload to a short human message, or null if unsafe/unknown.
 */
export function humanMessageFromPayload(payload) {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const { detail } = payload;
  if (typeof detail === "string") {
    const trimmed = detail.trim();
    if (!trimmed || SENSITIVE_DETAIL.test(trimmed)) {
      return null;
    }
    return BACKEND_DETAIL_TO_USER[trimmed] ?? trimmed;
  }

  if (!Array.isArray(detail)) {
    return null;
  }

  const parts = detail
    .map((item) => {
      if (!item || typeof item !== "object") {
        return "";
      }
      const msg = typeof item.msg === "string" ? item.msg.trim() : "";
      if (!msg || SENSITIVE_DETAIL.test(msg)) {
        return "";
      }
      const location = Array.isArray(item.loc)
        ? item.loc.filter((part) => part !== "body" && part !== "query").join(".")
        : "";
      return location ? `${location}: ${msg}` : msg;
    })
    .filter(Boolean);

  return parts.length > 0 ? parts.join(" ") : null;
}

/**
 * Choose a user-safe message for a non-OK HTTP response.
 */
export function messageForHttpFailure(status, payload) {
  const fromBody = humanMessageFromPayload(payload);
  if (fromBody) {
    return fromBody;
  }
  if (status === 404) {
    return USER_MESSAGES.httpNotFound;
  }
  if (status === 422) {
    return USER_MESSAGES.httpInvalid;
  }
  if (status >= 500) {
    return USER_MESSAGES.httpServer;
  }
  return USER_MESSAGES.httpGeneric;
}

/**
 * Parse JSON from a Response without throwing to the caller.
 */
export async function readJsonSafe(response) {
  try {
    const data = await response.json();
    return { ok: true, data };
  } catch {
    return { ok: false, data: null, message: USER_MESSAGES.malformed };
  }
}

/**
 * Normalize one supplier record for safe rendering.
 * Returns null when required identity fields are missing (not a silent fake success).
 */
export function normalizeSupplier(raw) {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  if (raw.id == null || raw.id === "") {
    return null;
  }

  const status = raw.status === "suspended" ? "suspended" : "active";
  const categories = Array.isArray(raw.categories)
    ? raw.categories.map((value) => String(value))
    : [];

  return {
    id: raw.id,
    name: String(raw.name ?? ""),
    country: String(raw.country ?? ""),
    categories,
    rate_per_unit: raw.rate_per_unit ?? "",
    currency: String(raw.currency ?? ""),
    status,
    contact_email: String(raw.contact_email ?? ""),
    notes: String(raw.notes ?? ""),
    updated_at: raw.updated_at ?? "",
  };
}

/**
 * Validate and normalize a supplier list payload.
 */
export function normalizeSupplierList(data) {
  if (!Array.isArray(data)) {
    return { ok: false, suppliers: [], message: USER_MESSAGES.invalidList };
  }

  const suppliers = [];
  for (const item of data) {
    const normalized = normalizeSupplier(item);
    if (normalized) {
      suppliers.push(normalized);
    }
  }

  return { ok: true, suppliers };
}
