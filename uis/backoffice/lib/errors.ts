const JWT_SHAPE = /^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/;

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function looksSensitive(value: string): boolean {
  return JWT_SHAPE.test(value.trim()) || /bearer\s+\S+/i.test(value);
}

export function publicErrorText(status: number, raw: string): string {
  const fallback = `Request failed (${status})`;
  const text = raw.trim();
  if (!text || looksSensitive(text)) {
    return fallback;
  }
  try {
    const data: unknown = JSON.parse(text);
    if (typeof data === "string") {
      const message = data.trim();
      return message && !looksSensitive(message) ? message : fallback;
    }
    const record = asRecord(data);
    const detail = record?.detail ?? record?.message ?? record?.error;
    if (typeof detail === "string") {
      const message = detail.trim();
      return message && !looksSensitive(message) ? message : fallback;
    }
    if (Array.isArray(detail)) {
      const parts = detail
        .map((item) => {
          const row = asRecord(item);
          return row && typeof row.msg === "string" ? row.msg.trim() : "";
        })
        .filter((part) => part.length > 0 && !looksSensitive(part));
      if (parts.length > 0) {
        return parts.join(" ");
      }
    }
  } catch {
    return fallback;
  }
  return fallback;
}
