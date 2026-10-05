"use client";

import { useCallback, useEffect, useState } from "react";
import { getRecords } from "@/lib/api";
import type { Candidate, RecordsQuery } from "@/types/candidate";

type AsyncStatus = "idle" | "loading" | "success" | "error";

export function useCandidates(query: RecordsQuery) {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<AsyncStatus>("idle");
  const [error, setError] = useState<string | null>(null);

  const statusFilter = query.status ?? "";
  const stageFilter = query.stage ?? "";
  const search = query.search ?? "";
  const page = query.page ?? 1;
  const limit = query.limit ?? 100;

  const load = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const response = await getRecords({
        status: statusFilter || undefined,
        stage: stageFilter || undefined,
        search: search || undefined,
        page,
        limit,
      });
      setCandidates(response.data);
      setTotal(response.total);
      setStatus("success");
    } catch (err) {
      setCandidates([]);
      setTotal(0);
      setStatus("error");
      setError(err instanceof Error ? err.message : "Failed to load candidates.");
    }
  }, [statusFilter, stageFilter, search, page, limit]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  return { candidates, total, status, error, reload: load };
}
