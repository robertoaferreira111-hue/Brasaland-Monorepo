"use client";

import { useCallback, useEffect, useState, useTransition } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { STAGE_OPTIONS, STATUS_OPTIONS } from "@/lib/labels";

export function CandidateFilters() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [, startTransition] = useTransition();

  const status = searchParams.get("status") ?? "";
  const stage = searchParams.get("stage") ?? "";
  const searchFromUrl = searchParams.get("search") ?? "";
  const [search, setSearch] = useState(searchFromUrl);
  const [previousUrlSearch, setPreviousUrlSearch] = useState(searchFromUrl);

  if (searchFromUrl !== previousUrlSearch) {
    setPreviousUrlSearch(searchFromUrl);
    setSearch(searchFromUrl);
  }

  const updateParams = useCallback(
    (next: { status?: string; stage?: string; search?: string }) => {
      const params = new URLSearchParams(searchParams.toString());

      (["status", "stage", "search"] as const).forEach((key) => {
        if (next[key] === undefined) return;
        const value = next[key]?.trim() ?? "";
        if (value) params.set(key, value);
        else params.delete(key);
      });

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
    const handle = window.setTimeout(() => {
      if (search === searchFromUrl) return;
      updateParams({ search });
    }, 300);
    return () => window.clearTimeout(handle);
  }, [search, searchFromUrl, updateParams]);

  return (
    <div className="grid gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 sm:grid-cols-3">
      <label className="grid gap-1 text-sm">
        <span className="font-medium text-[var(--ink)]">Search</span>
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Name or email"
          className="rounded-md border border-[var(--border)] bg-white px-3 py-2 text-[var(--ink)] outline-none ring-[var(--accent)] focus:ring-2"
        />
      </label>

      <label className="grid gap-1 text-sm">
        <span className="font-medium text-[var(--ink)]">Status</span>
        <select
          value={status}
          onChange={(event) => updateParams({ status: event.target.value })}
          className="rounded-md border border-[var(--border)] bg-white px-3 py-2 text-[var(--ink)] outline-none ring-[var(--accent)] focus:ring-2"
        >
          <option value="">All statuses</option>
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
          onChange={(event) => updateParams({ stage: event.target.value })}
          className="rounded-md border border-[var(--border)] bg-white px-3 py-2 text-[var(--ink)] outline-none ring-[var(--accent)] focus:ring-2"
        >
          <option value="">All stages</option>
          {STAGE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
