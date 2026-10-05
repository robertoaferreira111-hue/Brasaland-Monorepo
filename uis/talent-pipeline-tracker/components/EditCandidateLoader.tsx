"use client";

import Link from "next/link";
import { CandidateForm } from "@/components/CandidateForm";
import { FeedbackBanner } from "@/components/FeedbackBanner";
import { useCandidate } from "@/hooks/useCandidate";

export function EditCandidateLoader({ id }: { id: string }) {
  const { candidate, status, error, reload } = useCandidate(id);

  if (status === "loading" || status === "idle") {
    return <FeedbackBanner tone="info" message="Loading candidate…" />;
  }

  if (status === "error" || !candidate) {
    return (
      <div className="grid gap-2">
        <FeedbackBanner
          tone="error"
          message={error ?? "Candidate not found."}
        />
        <button
          type="button"
          onClick={() => void reload()}
          className="w-fit text-sm font-medium text-[var(--accent)] underline"
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      <div>
        <p className="text-sm text-[var(--muted)]">
          <Link href={`/candidates/${id}`} className="hover:underline">
            Back to candidate
          </Link>
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[var(--ink)]">
          Edit {candidate.full_name}
        </h1>
        <p className="text-sm text-[var(--muted)]">
          Correct candidate data when information arrives incomplete or wrong.
        </p>
      </div>
      <CandidateForm mode="edit" initialValues={candidate} />
    </div>
  );
}
