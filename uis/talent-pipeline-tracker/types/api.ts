/**
 * Canonical API types for the Talent Tracker (Phase 1).
 * Field names match the backend contract exactly.
 * Pre-existing `types/candidate.ts` is left untouched; prefer these types going forward.
 */

/** OpenAPI-documented status filter / record values (includes values not always present in live samples). */
export type CandidateStatus =
  | "received"
  | "in_progress"
  | "selected"
  | "discarded";

/** OpenAPI-documented stage filter / record values. */
export type CandidateStage =
  | "pending"
  | "review"
  | "personal_interview"
  | "technical_interview"
  | "offer_presented";

/** Note object returned by the API. */
export interface Note {
  id: string;
  record_id: string;
  content: string;
  created_at: string;
}

/**
 * Candidate record (`RecordOut`).
 * The undocumented `notes` array sometimes present on list items is optional
 * and must not be relied upon — use the notes endpoints instead.
 */
export interface CandidateRecord {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  position: string;
  linkedin_url: string | null;
  cv_url: string | null;
  status: CandidateStatus;
  stage: CandidateStage;
  experience_years: number;
  notes_count: number;
  applied_at: string;
  updated_at: string;
  /** Undocumented on list responses only; do not rely on this field. */
  notes?: Note[];
}

/** POST /records and PUT /records/:id body (`RecordCreate`). */
export interface CandidateCreatePayload {
  full_name: string;
  email: string;
  phone: string;
  position: string;
  experience_years: number;
  linkedin_url?: string | null;
  cv_url?: string | null;
}

/** Alias: full-update payload is the same shape as create. */
export type CandidateUpdatePayload = CandidateCreatePayload;

/** PATCH /records/:id body (`RecordPatch`). */
export interface CandidatePatchPayload {
  status?: CandidateStatus | null;
  stage?: CandidateStage | null;
}

/** POST /records/:id/notes body (`NoteCreate`). */
export interface NoteCreatePayload {
  content: string;
}

/** GET /records response envelope. */
export interface RecordsListEnvelope {
  total: number;
  page: number;
  limit: number;
  data: CandidateRecord[];
}

/** GET /records/:id/notes response envelope. */
export interface NotesListEnvelope {
  data: Note[];
  meta: {
    total: number;
  };
}

/** Filters for listing candidates (Phase 2 list UI). */
export interface CandidateListFilters {
  status?: CandidateStatus;
  stage?: CandidateStage;
  search?: string;
  page?: number;
  limit?: number;
}

/**
 * Consistent typed API error for network failures, non-2xx responses,
 * and malformed JSON.
 */
export interface ApiErrorShape {
  name: "ApiError";
  message: string;
  status: number | null;
  cause?: unknown;
}

export class ApiError extends Error implements ApiErrorShape {
  readonly name = "ApiError" as const;
  readonly status: number | null;
  readonly cause?: unknown;

  constructor(message: string, status: number | null = null, cause?: unknown) {
    super(message);
    this.status = status;
    this.cause = cause;
  }
}

/** Unwrapped list result for service callers. */
export interface CandidateListResult {
  items: CandidateRecord[];
  total: number;
  page: number;
  limit: number;
}
