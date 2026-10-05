"use client";

import { STAGE_OPTIONS, STATUS_OPTIONS } from "@/lib/labels";
import type { CandidateStage, CandidateStatus } from "@/types/api";
import { FeedbackBanner } from "@/components/FeedbackBanner";

type PipelineControlsProps = {
  status: CandidateStatus;
  stage: CandidateStage;
  patchStatus: "idle" | "loading" | "success" | "error";
  patchError: string | null;
  patchSuccess: string | null;
  onStatusChange: (status: CandidateStatus) => void;
  onStageChange: (stage: CandidateStage) => void;
};

export function PipelineControls({
  status,
  stage,
  patchStatus,
  patchError,
  patchSuccess,
  onStatusChange,
  onStageChange,
}: PipelineControlsProps) {
  const busy = patchStatus === "loading";

  return (
    <section className="grid gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
      <div>
        <h2 className="text-lg font-semibold text-[var(--ink)]">
          Update status or stage
        </h2>
        <p className="text-sm text-[var(--muted)]">
          Move this applicant through the Brasaland People &amp; Talent process
          with a single selection.
        </p>
      </div>

      {busy && <FeedbackBanner tone="info" message="Saving change…" />}
      {patchError && <FeedbackBanner tone="error" message={patchError} />}
      {patchSuccess && (
        <FeedbackBanner tone="success" message={patchSuccess} />
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="grid gap-1 text-sm">
          <span className="font-medium text-[var(--ink)]">Status</span>
          <select
            value={status}
            disabled={busy}
            onChange={(event) =>
              onStatusChange(event.target.value as CandidateStatus)
            }
            className="rounded-md border border-[var(--border)] bg-white px-3 py-2 text-[var(--ink)] outline-none ring-[var(--accent)] focus:ring-2 disabled:opacity-60"
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="grid gap-1 text-sm">
          <span className="font-medium text-[var(--ink)]">Stage</span>
          <select
            value={stage}
            disabled={busy}
            onChange={(event) =>
              onStageChange(event.target.value as CandidateStage)
            }
            className="rounded-md border border-[var(--border)] bg-white px-3 py-2 text-[var(--ink)] outline-none ring-[var(--accent)] focus:ring-2 disabled:opacity-60"
          >
            {STAGE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>
    </section>
  );
}
