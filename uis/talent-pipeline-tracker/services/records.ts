import { apiRequest } from "@/lib/httpClient";
import type {
  CandidateCreatePayload,
  CandidateListFilters,
  CandidateListResult,
  CandidatePatchPayload,
  CandidateRecord,
  CandidateUpdatePayload,
  RecordsListEnvelope,
} from "@/types/api";

function buildListQuery(filters: CandidateListFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.stage) params.set("stage", filters.stage);
  if (filters.search?.trim()) params.set("search", filters.search.trim());
  if (filters.page !== undefined) params.set("page", String(filters.page));
  if (filters.limit !== undefined) params.set("limit", String(filters.limit));
  const query = params.toString();
  return query ? `?${query}` : "";
}

/** GET /records — returns unwrapped list result. */
export async function listCandidates(
  filters: CandidateListFilters = {},
): Promise<CandidateListResult> {
  const envelope = await apiRequest<RecordsListEnvelope>(
    `/records${buildListQuery(filters)}`,
  );
  return {
    items: envelope.data,
    total: envelope.total,
    page: envelope.page,
    limit: envelope.limit,
  };
}

/** GET /records/:id */
export async function getCandidate(id: string): Promise<CandidateRecord> {
  return apiRequest<CandidateRecord>(`/records/${id}`);
}

/** POST /records */
export async function createCandidate(
  payload: CandidateCreatePayload,
): Promise<CandidateRecord> {
  return apiRequest<CandidateRecord>("/records", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** PUT /records/:id */
export async function updateCandidate(
  id: string,
  payload: CandidateUpdatePayload,
): Promise<CandidateRecord> {
  return apiRequest<CandidateRecord>(`/records/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

/** PATCH /records/:id (status and/or stage) */
export async function patchCandidate(
  id: string,
  payload: CandidatePatchPayload,
): Promise<CandidateRecord> {
  return apiRequest<CandidateRecord>(`/records/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
