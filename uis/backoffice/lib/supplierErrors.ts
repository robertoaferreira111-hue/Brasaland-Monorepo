export const USER_MESSAGES = {
  network: "We could not reach the supplier service. Check your connection, then try again. If this keeps happening, contact support.",
  httpGeneric: "We could not complete that request. Try again. If the problem continues, contact support.",
  httpNotFound: "That supplier was not found. Refresh the list and try again, or contact support.",
  httpInvalid: "Some of the submitted values are invalid. Check the highlighted fields and try again.",
  httpServer: "The supplier service had a problem. Try again in a moment. If it continues, contact support.",
  storageUnavailable: "The supplier database is temporarily unavailable. Try again. If this continues, contact support.",
  storedDataInvalid: "That supplier record is damaged and cannot be shown. Try again later, or contact support.",
  unexpectedServer: "Something went wrong on the server. Try again. If this continues, contact support.",
  malformed: "The supplier service returned an unexpected response. Try again, or contact support.",
  invalidList: "The supplier list was incomplete or invalid. Try again, or contact support.",
};

export type Supplier = {
  id: string | number;
  name: string;
  country: string;
  categories: string[];
  rate_per_unit: string | number;
  currency: string;
  status: "active" | "suspended";
  contact_email: string;
  notes: string;
  updated_at: string;
};

const safeDetails: Record<string, string> = {
  "Storage unavailable": USER_MESSAGES.storageUnavailable,
  "Stored supplier data is invalid": USER_MESSAGES.storedDataInvalid,
  "An unexpected error occurred": USER_MESSAGES.unexpectedServer,
  "Supplier not found": USER_MESSAGES.httpNotFound,
};
const sensitive = /traceback|file\s+"|\/users\/|\/home\/|\\|password\s*=|secret|api[_-]?key|suppliers\.json/i;

export function humanMessageFromPayload(payload: unknown): string | null {
  if (!payload || typeof payload !== "object") return null;
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string") {
    const value = detail.trim();
    return !value || sensitive.test(value) ? null : safeDetails[value] ?? value;
  }
  if (!Array.isArray(detail)) return null;
  const parts = detail.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const entry = item as { msg?: unknown; loc?: unknown };
    const message = typeof entry.msg === "string" ? entry.msg.trim() : "";
    if (!message || sensitive.test(message)) return [];
    const location = Array.isArray(entry.loc)
      ? entry.loc.filter((part) => part !== "body" && part !== "query").join(".")
      : "";
    return [location ? `${location}: ${message}` : message];
  });
  return parts.length ? parts.join(" ") : null;
}

export function messageForHttpFailure(status: number, payload: unknown) {
  const message = humanMessageFromPayload(payload);
  if (message) return message;
  if (status === 404) return USER_MESSAGES.httpNotFound;
  if (status === 422) return USER_MESSAGES.httpInvalid;
  return status >= 500 ? USER_MESSAGES.httpServer : USER_MESSAGES.httpGeneric;
}

export async function readJsonSafe(response: Response) {
  try {
    return { ok: true as const, data: await response.json() as unknown };
  } catch {
    return { ok: false as const, data: null, message: USER_MESSAGES.malformed };
  }
}

export function normalizeSupplier(raw: unknown): Supplier | null {
  if (!raw || typeof raw !== "object") return null;
  const value = raw as Record<string, unknown>;
  if (value.id == null || value.id === "") return null;
  return {
    id: value.id as string | number,
    name: String(value.name ?? ""),
    country: String(value.country ?? ""),
    categories: Array.isArray(value.categories) ? value.categories.map(String) : [],
    rate_per_unit: (value.rate_per_unit ?? "") as string | number,
    currency: String(value.currency ?? ""),
    status: value.status === "suspended" ? "suspended" : "active",
    contact_email: String(value.contact_email ?? ""),
    notes: String(value.notes ?? ""),
    updated_at: String(value.updated_at ?? ""),
  };
}

export function normalizeSupplierList(data: unknown) {
  if (!Array.isArray(data)) return { ok: false as const, suppliers: [], message: USER_MESSAGES.invalidList };
  return {
    ok: true as const,
    suppliers: data.map(normalizeSupplier).filter((item): item is Supplier => item !== null),
  };
}
