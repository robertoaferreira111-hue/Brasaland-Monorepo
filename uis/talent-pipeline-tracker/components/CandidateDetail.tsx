"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { FeedbackBanner } from "@/components/FeedbackBanner";
import { ListNavLink } from "@/components/ListNavLink";
import { NotesPanel } from "@/components/NotesPanel";
import { PipelineControls } from "@/components/PipelineControls";
import { StageBadge } from "@/components/StageBadge";
import { StatusBadge } from "@/components/StatusBadge";
import { useAsync } from "@/hooks/useAsync";
import { getCandidate, patchCandidate } from "@/services/records";
import type {
  CandidateRecord,
  CandidateStage,
  CandidateStatus,
} from "@/types/api";
import { ApiError } from "@/types/api";

function isSafeHttpUrl(value: string | null | undefined): value is string {
  if (!value) return false;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

function noticeMessage(notice: string | null): string | null {
  if (notice === "registered") return "Candidate registered successfully.";
  if (notice === "updated") return "Candidate updated successfully.";
  return null;
}

export function CandidateDetail({ id }: { id: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const returnQuery = searchParams.get("return");
  const noticeParam = searchParams.get("notice");
  const [formNotice] = useState(() => noticeMessage(noticeParam));

  const loader = useCallback(() => getCandidate(id), [id]);
  const { data, error, errorStatus, status, refetch } = useAsync(loader);

  const [patched, setPatched] = useState<CandidateRecord | null>(null);
  const [patchedForId, setPatchedForId] = useState<string | null>(null);
  const candidate =
    patched && patchedForId === id ? patched : data;

  const [patchStatus, setPatchStatus] = useState<
    "idle" | "loading" | "success" | "error"
  >("idle");
  const [patchError, setPatchError] = useState<string | null>(null);
  const [patchSuccess, setPatchSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!noticeParam) return;
    const params = new URLSearchParams(searchParams.toString());
    if (!params.has("notice")) return;
    params.delete("notice");
    const query = params.toString();
    const timer = window.setTimeout(() => {
      router.replace(query ? `${pathname}?${query}` : pathname, {
        scroll: false,
      });
    }, 0);
    return () => window.clearTimeout(timer);
  }, [noticeParam, pathname, router, searchParams]);

  async function applyPatch(
    payload: { status?: CandidateStatus; stage?: CandidateStage },
    successMessage: string,
  ) {
    setPatchStatus("loading");
    setPatchError(null);
    setPatchSuccess(null);
    try {
      const updated = await patchCandidate(id, payload);
      setPatched(updated);
      setPatchedForId(id);
      setPatchStatus("success");
      setPatchSuccess(successMessage);
      await refetch({ keepPreviousData: true });
    } catch (err) {
      setPatchStatus("error");
      setPatchError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Failed to update candidate.",
      );
    }
  }

  if (!candidate && (status === "loading" || status === "idle")) {
    return <FeedbackBanner tone="info" message="Loading candidate…" />;
  }

  const notFound = status === "error" && errorStatus === 404;

  if (!candidate) {
    return (
      <div className="grid gap-3">
        <FeedbackBanner
          tone="error"
          message={
            notFound
              ? "Candidate not found. It may have been removed or the link is invalid."
              : (error ?? "Failed to load candidate.")
          }
        />
        <div className="flex flex-wrap gap-3">
          {!notFound ? (
            <button
              type="button"
              onClick={() => void refetch()}
              className="w-fit text-sm font-medium text-[var(--accent)] underline"
            >
              Try again
            </button>
          ) : null}
          <ListNavLink className="w-fit text-sm font-medium text-[var(--accent)] underline">
            Back to candidates
          </ListNavLink>
        </div>
      </div>
    );
  }

  const editHref = returnQuery
    ? `/candidates/${candidate.id}/edit?return=${encodeURIComponent(returnQuery)}`
    : `/candidates/${candidate.id}/edit`;

  return (
    <div className="grid gap-6">
      {formNotice ? (
        <FeedbackBanner tone="success" message={formNotice} />
      ) : null}

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm text-[var(--muted)]">
            <ListNavLink className="hover:underline">Candidates</ListNavLink> /{" "}
            {candidate.full_name}
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
          href={editHref}
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
            isSafeHttpUrl(candidate.linkedin_url) ? (
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
            isSafeHttpUrl(candidate.cv_url) ? (
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
          label="Status"
          value={<StatusBadge status={candidate.status} />}
        />
        <DetailItem
          label="Stage"
          value={<StageBadge stage={candidate.stage} />}
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
        onStatusChange={(next) =>
          void applyPatch({ status: next }, "Status updated successfully.")
        }
        onStageChange={(next) =>
          void applyPatch({ stage: next }, "Stage updated successfully.")
        }
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
