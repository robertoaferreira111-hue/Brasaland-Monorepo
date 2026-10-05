"use client";

import Link from "next/link";
import { useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { CandidateForm } from "@/components/CandidateForm";
import { FeedbackBanner } from "@/components/FeedbackBanner";
import { ListNavLink } from "@/components/ListNavLink";
import { useAsync } from "@/hooks/useAsync";
import { getCandidate } from "@/services/records";

export function EditCandidateLoader({ id }: { id: string }) {
  const searchParams = useSearchParams();
  const returnQuery = searchParams.get("return");
  const loader = useCallback(() => getCandidate(id), [id]);
  const { data, error, errorStatus, status, refetch } = useAsync(loader);

  if (status === "loading" || status === "idle") {
    return <FeedbackBanner tone="info" message="Loading candidate…" />;
  }

  const notFound = status === "error" && errorStatus === 404;

  if (status === "error" || !data) {
    return (
      <div className="grid gap-2">
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

  const backHref = returnQuery
    ? `/candidates/${id}?return=${encodeURIComponent(returnQuery)}`
    : `/candidates/${id}`;

  return (
    <div className="grid gap-4">
      <div>
        <p className="text-sm text-[var(--muted)]">
          <Link href={backHref} className="hover:underline">
            Back to candidate
          </Link>
          {" · "}
          <ListNavLink className="hover:underline">Candidates</ListNavLink>
        </p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[var(--ink)]">
          Edit {data.full_name}
        </h1>
        <p className="text-sm text-[var(--muted)]">
          Correct candidate data when information arrives incomplete or wrong.
        </p>
      </div>
      <CandidateForm
        mode="edit"
        initialValues={data}
        returnQuery={returnQuery}
      />
    </div>
  );
}
