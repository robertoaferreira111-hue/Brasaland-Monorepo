"use client";

import Link from "next/link";
import { useCallback, useEffect, useTransition } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { FeedbackBanner } from "@/components/FeedbackBanner";
import { StageBadge } from "@/components/StageBadge";
import { StatusBadge } from "@/components/StatusBadge";
import { useAsync } from "@/hooks/useAsync";
import { STAGE_OPTIONS, STATUS_OPTIONS } from "@/lib/labels";
import { buildDetailHref } from "@/lib/listNavigation";
import { listCandidates } from "@/services/records";
import type {
  CandidateListResult,
  CandidateStage,
  CandidateStatus,
} from "@/types/api";

const PAGE_SIZE = 20;

const STATUS_VALUES = new Set(STATUS_OPTIONS.map((option) => option.value));
const STAGE_VALUES = new Set(STAGE_OPTIONS.map((option) => option.value));

function parsePage(raw: string | null): number {
  const value = Number(raw ?? "1");
  if (!Number.isFinite(value) || value < 1) return 1;
  return Math.floor(value);
}

function parseStatus(raw: string | null): CandidateStatus | undefined {
  if (!raw || !STATUS_VALUES.has(raw as CandidateStatus)) return undefined;
  return raw as CandidateStatus;
}

function parseStage(raw: string | null): CandidateStage | undefined {
  if (!raw || !STAGE_VALUES.has(raw as CandidateStage)) return undefined;
  return raw as CandidateStage;
}

export function CandidateList() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [, startTransition] = useTransition();

  const status = parseStatus(searchParams.get("status"));
  const stage = parseStage(searchParams.get("stage"));
  const search = searchParams.get("search")?.trim() ?? "";
  const page = parsePage(searchParams.get("page"));

  const loader = useCallback((): Promise<CandidateListResult> => {
    return listCandidates({
      status,
      stage,
      search: search || undefined,
      page,
      limit: PAGE_SIZE,
    });
  }, [status, stage, search, page]);

  const { data, error, status: asyncStatus, refetch } = useAsync(loader);

  const total = data?.total ?? 0;
  const candidates = data?.items ?? [];
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const goToPage = useCallback(
    (nextPage: number) => {
      const params = new URLSearchParams(searchParams.toString());
      if (nextPage <= 1) params.delete("page");
      else params.set("page", String(nextPage));
      const query = params.toString();
      startTransition(() => {
        router.replace(query ? `${pathname}?${query}` : pathname, {
          scroll: false,
        });
      });
    },
    [pathname, router, searchParams, startTransition],
  );

  useEffect(() => {
    if (asyncStatus !== "success" || total === 0) return;
    if (page > totalPages) goToPage(totalPages);
  }, [asyncStatus, goToPage, page, total, totalPages]);

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
          <p className="text-sm text-[var(--muted)]">
            {total} candidates
            {totalPages > 1 ? ` · Page ${page} of ${totalPages}` : null}
          </p>
        )}
      </div>

      {asyncStatus === "loading" || asyncStatus === "idle" ? (
        <FeedbackBanner tone="info" message="Loading candidates…" />
      ) : null}

      {asyncStatus === "error" && error ? (
        <div className="grid gap-2">
          <FeedbackBanner tone="error" message={error} />
          <button
            type="button"
            onClick={() => void refetch()}
            className="w-fit text-sm font-medium text-[var(--accent)] underline"
          >
            Try again
          </button>
        </div>
      ) : null}

      {asyncStatus === "success" && candidates.length === 0 ? (
        <FeedbackBanner
          tone="info"
          message="No candidates match the current filters."
        />
      ) : null}

      {asyncStatus === "success" && candidates.length > 0 ? (
        <>
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
                        href={buildDetailHref(
                          candidate.id,
                          searchParams.toString(),
                        )}
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

          {totalPages > 1 ? (
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => goToPage(page - 1)}
                className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm font-medium text-[var(--ink)] disabled:cursor-not-allowed disabled:opacity-50"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => goToPage(page + 1)}
                className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm font-medium text-[var(--ink)] disabled:cursor-not-allowed disabled:opacity-50"
              >
                Next
              </button>
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
