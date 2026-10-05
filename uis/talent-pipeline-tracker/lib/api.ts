import type {
  Candidate,
  CandidateCreate,
  CandidatePatch,
  Note,
  NotesListResponse,
  RecordsListResponse,
  RecordsQuery,
} from "@/types/candidate";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

if (!API_URL) {
  console.warn(
    "NEXT_PUBLIC_API_URL is not set. API requests will fail until it is configured.",
  );
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  if (!API_URL) {
    throw new ApiError(
      "API URL is not configured. Set NEXT_PUBLIC_API_URL in .env.local.",
      0,
    );
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...(options.headers ?? {}),
    },
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as {
        detail?: string | { msg?: string }[];
      };
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (Array.isArray(body.detail) && body.detail[0]?.msg) {
        message = body.detail.map((item) => item.msg).join(", ");
      }
    } catch {
      // keep default message
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

function buildQuery(params: RecordsQuery): string {
  const searchParams = new URLSearchParams();
  if (params.status) searchParams.set("status", params.status);
  if (params.stage) searchParams.set("stage", params.stage);
  if (params.search?.trim()) searchParams.set("search", params.search.trim());
  if (params.page) searchParams.set("page", String(params.page));
  if (params.limit) searchParams.set("limit", String(params.limit));
  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

export async function getRecords(
  params: RecordsQuery = {},
): Promise<RecordsListResponse> {
  return request<RecordsListResponse>(`/records${buildQuery(params)}`);
}

export async function getRecord(id: string): Promise<Candidate> {
  return request<Candidate>(`/records/${id}`);
}

export async function createRecord(
  payload: CandidateCreate,
): Promise<Candidate> {
  return request<Candidate>("/records", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateRecord(
  id: string,
  payload: CandidateCreate,
): Promise<Candidate> {
  return request<Candidate>(`/records/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function patchRecord(
  id: string,
  payload: CandidatePatch,
): Promise<Candidate> {
  return request<Candidate>(`/records/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function getNotes(id: string): Promise<NotesListResponse> {
  return request<NotesListResponse>(`/records/${id}/notes`);
}

export async function createNote(
  id: string,
  content: string,
): Promise<Note> {
  return request<Note>(`/records/${id}/notes`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export async function deleteNote(
  id: string,
  noteId: string,
): Promise<void> {
  return request<void>(`/records/${id}/notes/${noteId}`, {
    method: "DELETE",
  });
}
