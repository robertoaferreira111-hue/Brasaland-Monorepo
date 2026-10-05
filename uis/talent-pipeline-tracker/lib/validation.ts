import type { CandidateCreatePayload } from "@/types/api";
import { ApiError } from "@/types/api";

export type FormErrors = Partial<Record<keyof CandidateCreatePayload, string>>;

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Client validation aligned with live API requirements:
 * required: full_name, email, phone, position, experience_years
 * email must contain @ (422 value_error from API)
 * linkedin_url / cv_url optional; when present must be valid URLs
 *
 * Note: the live API accepts an empty-string full_name if the key is present;
 * we still require a non-empty name in the UI for usable People & Talent records.
 */
export function validateCandidateForm(
  values: CandidateCreatePayload,
): FormErrors {
  const errors: FormErrors = {};

  if (!String(values.full_name ?? "").trim()) {
    errors.full_name = "Full name is required.";
  }

  const email = String(values.email ?? "").trim();
  if (!email) {
    errors.email = "Email is required.";
  } else if (!EMAIL_PATTERN.test(email)) {
    errors.email = "Enter a valid email address.";
  }

  if (!String(values.phone ?? "").trim()) {
    errors.phone = "Phone is required.";
  }

  if (!String(values.position ?? "").trim()) {
    errors.position = "Position is required.";
  }

  if (
    values.experience_years === undefined ||
    values.experience_years === null ||
    Number.isNaN(Number(values.experience_years))
  ) {
    errors.experience_years = "Years of experience is required.";
  } else if (Number(values.experience_years) < 0) {
    errors.experience_years = "Years of experience cannot be negative.";
  }

  const linkedin = values.linkedin_url?.toString().trim();
  if (linkedin) {
    try {
      const url = new URL(linkedin);
      if (url.protocol !== "http:" && url.protocol !== "https:") {
        errors.linkedin_url = "Enter a valid LinkedIn URL.";
      }
    } catch {
      errors.linkedin_url = "Enter a valid LinkedIn URL.";
    }
  }

  const cv = values.cv_url?.toString().trim();
  if (cv) {
    try {
      const url = new URL(cv);
      if (url.protocol !== "http:" && url.protocol !== "https:") {
        errors.cv_url = "Enter a valid CV URL.";
      }
    } catch {
      errors.cv_url = "Enter a valid CV URL.";
    }
  }

  return errors;
}

export function hasFormErrors(errors: FormErrors): boolean {
  return Object.keys(errors).length > 0;
}

/** Full PUT/POST body — always includes optional URL fields (null when cleared). */
export function toCandidatePayload(
  values: CandidateCreatePayload,
): CandidateCreatePayload {
  return {
    full_name: String(values.full_name).trim(),
    email: String(values.email).trim(),
    phone: String(values.phone).trim(),
    position: String(values.position).trim(),
    experience_years: Number(values.experience_years),
    linkedin_url: values.linkedin_url?.toString().trim() || null,
    cv_url: values.cv_url?.toString().trim() || null,
  };
}

/** Map FastAPI 422 `detail` (or `{ error, details }`) onto form fields when possible. */
export function fieldErrorsFromApiError(error: unknown): FormErrors {
  const errors: FormErrors = {};
  if (!(error instanceof ApiError) || error.cause == null) return errors;

  const body = error.cause;
  if (typeof body !== "object") return errors;
  const record = body as Record<string, unknown>;

  if (Array.isArray(record.detail)) {
    for (const item of record.detail) {
      if (!item || typeof item !== "object") continue;
      const entry = item as { loc?: unknown; msg?: unknown };
      const loc = Array.isArray(entry.loc) ? entry.loc : [];
      const field = loc.find(
        (part): part is string =>
          typeof part === "string" &&
          part !== "body" &&
          part !== "query" &&
          part !== "path",
      );
      if (
        field &&
        typeof entry.msg === "string" &&
        isFormField(field) &&
        !errors[field]
      ) {
        errors[field] = humanizeApiMessage(field, entry.msg);
      }
    }
  }

  if (record.details && typeof record.details === "object") {
    for (const [key, value] of Object.entries(
      record.details as Record<string, unknown>,
    )) {
      if (isFormField(key) && typeof value === "string" && !errors[key]) {
        errors[key] = value;
      }
    }
  }

  return errors;
}

function isFormField(key: string): key is keyof CandidateCreatePayload {
  return [
    "full_name",
    "email",
    "phone",
    "position",
    "experience_years",
    "linkedin_url",
    "cv_url",
  ].includes(key);
}

function humanizeApiMessage(field: string, msg: string): string {
  if (field === "email" && msg.toLowerCase().includes("email")) {
    return "Enter a valid email address.";
  }
  return msg;
}
