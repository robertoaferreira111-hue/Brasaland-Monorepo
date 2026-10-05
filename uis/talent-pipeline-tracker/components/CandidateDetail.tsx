"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { FeedbackBanner } from "@/components/FeedbackBanner";
import { NotesPanel } from "@/components/NotesPanel";
import { PipelineControls } from "@/components/PipelineControls";
import { StageBadge } from "@/components/StageBadge";
import { StatusBadge } from "@/components/StatusBadge";
import { useCandidate } from "@/hooks/useCandidate";

export function CandidateDetail({ id }: { id: string }) {
  const {
    candidate,
    status,
    error,
    patchStatus,
    patchError,
    patchSuccess,
    updateStatus,
    updateStage,
    reload,
  } = useCandidate(id);

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
    <div className="grid gap-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm text-[var(--muted)]">
            <Link href="/" className="hover:underline">
              Candidates
            </Link>{" "}
            / {candidate.full_name}
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[var(--ink)]">
            {candidate.full_name}
          </h1>
          <div className="mt-2 flex flex-wrap gap-2">
            <StatusBadge status={candidate.status} />
            <StageBadge stage={candidate.stage} />
          </div>
        </div>
        <Link
          href={`/candidates/${candidate.id}/edit`}
          className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm font-semibold text-[var(--ink)] hover:bg-[var(--surface-muted)]"
        >
          Edit candidate
        </Link>
      </div>

      <section className="grid gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 sm:grid-cols-2">
        <DetailItem label="Email" value={candidate.email} />
        <DetailItem label="Phone" value={candidate.phone} />
        <DetailItem label="Position" value={candidate.position} />
        <DetailItem
          label="Years of experience"
          value={String(candidate.experience_years)}
        />
        <DetailItem
          label="LinkedIn"
          value={
            candidate.linkedin_url ? (
              <a
                href={candidate.linkedin_url}
                target="_blank"
                rel="noreferrer"
                className="text-[var(--accent)] hover:underline"
              >
                Open profile
              </a>
            ) : (
              "—"
            )
          }
        />
        <DetailItem
          label="CV"
          value={
            candidate.cv_url ? (
              <a
                href={candidate.cv_url}
                target="_blank"
                rel="noreferrer"
                className="text-[var(--accent)] hover:underline"
              >
                Open CV
              </a>
            ) : (
              "—"
            )
          }
        />
        <DetailItem
          label="Applied"
          value={new Date(candidate.applied_at).toLocaleString()}
        />
        <DetailItem
          label="Last updated"
          value={new Date(candidate.updated_at).toLocaleString()}
        />
      </section>

      <PipelineControls
        status={candidate.status}
        stage={candidate.stage}
        patchStatus={patchStatus}
        patchError={patchError}
        patchSuccess={patchSuccess}
        onStatusChange={(next) => void updateStatus(next)}
        onStageChange={(next) => void updateStage(next)}
      />

      <NotesPanel recordId={candidate.id} />
    </div>
  );
}

function DetailItem({
  label,
  value,
}: {
  label: string;
  value: ReactNode;
}) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
        {label}
      </dt>
      <dd className="mt-1 text-sm text-[var(--ink)]">{value}</dd>
    </div>
  );
}
