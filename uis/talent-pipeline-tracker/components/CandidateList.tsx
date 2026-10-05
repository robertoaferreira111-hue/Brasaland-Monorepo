"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FeedbackBanner } from "@/components/FeedbackBanner";
import { StageBadge } from "@/components/StageBadge";
import { StatusBadge } from "@/components/StatusBadge";
import { useCandidates } from "@/hooks/useCandidates";
import type { CandidateStage, CandidateStatus } from "@/types/candidate";

export function CandidateList() {
  const searchParams = useSearchParams();
  const status = (searchParams.get("status") ?? "") as CandidateStatus | "";
  const stage = (searchParams.get("stage") ?? "") as CandidateStage | "";
  const search = searchParams.get("search") ?? "";

  const { candidates, total, status: asyncStatus, error, reload } =
    useCandidates({
      status,
      stage,
      search,
      page: 1,
      limit: 100,
    });

  return (
    <section className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--ink)]">
            Candidate pipeline
          </h1>
          <p className="text-sm text-[var(--muted)]">
            Active search for Executive Assistant · Corporate headquarters,
            Medellín
          </p>
        </div>
        {asyncStatus === "success" && (
          <p className="text-sm text-[var(--muted)]">{total} candidates</p>
        )}
      </div>

      {asyncStatus === "loading" && (
        <FeedbackBanner tone="info" message="Loading candidates…" />
      )}
      {asyncStatus === "error" && error && (
        <div className="grid gap-2">
          <FeedbackBanner tone="error" message={error} />
          <button
            type="button"
            onClick={() => void reload()}
            className="w-fit text-sm font-medium text-[var(--accent)] underline"
          >
            Try again
          </button>
        </div>
      )}

      {asyncStatus === "success" && candidates.length === 0 && (
        <FeedbackBanner
          tone="info"
          message="No candidates match the current filters."
        />
      )}

      {candidates.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-[var(--border)] bg-[var(--surface)]">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-[var(--border)] bg-[var(--surface-muted)] text-[var(--muted)]">
              <tr>
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Position</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Stage</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((candidate) => (
                <tr
                  key={candidate.id}
                  className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--surface-muted)]/70"
                >
                  <td className="px-4 py-3">
                    <Link
                      href={`/candidates/${candidate.id}`}
                      className="font-medium text-[var(--accent)] hover:underline"
                    >
                      {candidate.full_name}
                    </Link>
                    <p className="text-xs text-[var(--muted)]">
                      {candidate.email}
                    </p>
                  </td>
                  <td className="px-4 py-3 text-[var(--ink)]">
                    {candidate.position}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={candidate.status} />
                  </td>
                  <td className="px-4 py-3">
                    <StageBadge stage={candidate.stage} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
