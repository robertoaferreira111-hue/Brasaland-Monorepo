"use client";

import { useCallback, useEffect, useState } from "react";
import { getRecord, patchRecord } from "@/lib/api";
import type {
  Candidate,
  CandidatePatch,
  CandidateStage,
  CandidateStatus,
} from "@/types/candidate";

type AsyncStatus = "idle" | "loading" | "success" | "error";

export function useCandidate(id: string) {
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [status, setStatus] = useState<AsyncStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [patchStatus, setPatchStatus] = useState<AsyncStatus>("idle");
  const [patchError, setPatchError] = useState<string | null>(null);
  const [patchSuccess, setPatchSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const data = await getRecord(id);
      setCandidate(data);
      setStatus("success");
    } catch (err) {
      setCandidate(null);
      setStatus("error");
      setError(err instanceof Error ? err.message : "Failed to load candidate.");
    }
  }, [id]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const updateField = useCallback(
    async (payload: CandidatePatch, successMessage: string) => {
      setPatchStatus("loading");
      setPatchError(null);
      setPatchSuccess(null);
      try {
        const updated = await patchRecord(id, payload);
        setCandidate(updated);
        setPatchStatus("success");
        setPatchSuccess(successMessage);
      } catch (err) {
        setPatchStatus("error");
        setPatchError(
          err instanceof Error ? err.message : "Failed to update candidate.",
        );
      }
    },
    [id],
  );

  const updateStatus = useCallback(
    (next: CandidateStatus) =>
      updateField({ status: next }, "Status updated successfully."),
    [updateField],
  );

  const updateStage = useCallback(
    (next: CandidateStage) =>
      updateField({ stage: next }, "Stage updated successfully."),
    [updateField],
  );

  return {
    candidate,
    status,
    error,
    patchStatus,
    patchError,
    patchSuccess,
    reload: load,
    updateStatus,
    updateStage,
  };
}
