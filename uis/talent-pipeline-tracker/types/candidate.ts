export type CandidateStatus =
  | "received"
  | "in_progress"
  | "selected"
  | "discarded";

export type CandidateStage =
  | "pending"
  | "review"
  | "personal_interview"
  | "technical_interview"
  | "offer_presented";

export interface Note {
  id: string;
  record_id: string;
  content: string;
  created_at: string;
}

export interface Candidate {
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
  notes?: Note[];
}

export interface CandidateCreate {
  full_name: string;
  email: string;
  phone: string;
  position: string;
  experience_years: number;
  linkedin_url?: string | null;
  cv_url?: string | null;
}

export interface CandidatePatch {
  status?: CandidateStatus;
  stage?: CandidateStage;
}

export interface RecordsListResponse {
  total: number;
  page: number;
  limit: number;
  data: Candidate[];
}

export interface NotesListResponse {
  data: Note[];
  meta: {
    total: number;
  };
}

export interface RecordsQuery {
  status?: CandidateStatus | "";
  stage?: CandidateStage | "";
  search?: string;
  page?: number;
  limit?: number;
}
