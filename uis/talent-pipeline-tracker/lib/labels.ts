import type { CandidateStage, CandidateStatus } from "@/types/api";

export const STATUS_LABELS: Record<CandidateStatus, string> = {
  received: "Received",
  in_progress: "In progress",
  selected: "Selected",
  discarded: "Discarded",
};

export const STAGE_LABELS: Record<CandidateStage, string> = {
  pending: "Pending review",
  review: "Under review",
  personal_interview: "Personal interview",
  technical_interview: "Technical interview",
  offer_presented: "Offer presented",
};

export const STATUS_OPTIONS = Object.entries(STATUS_LABELS).map(
  ([value, label]) => ({
    value: value as CandidateStatus,
    label,
  }),
);

export const STAGE_OPTIONS = Object.entries(STAGE_LABELS).map(
  ([value, label]) => ({
    value: value as CandidateStage,
    label,
  }),
);

export function statusLabel(status: CandidateStatus): string {
  return STATUS_LABELS[status] ?? status;
}

export function stageLabel(stage: CandidateStage): string {
  return STAGE_LABELS[stage] ?? stage;
}
