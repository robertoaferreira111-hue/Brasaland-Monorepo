"use client";

import { useCallback, useEffect, useState } from "react";

type AsyncStatus = "idle" | "loading" | "success" | "error";

export type UseAsyncResult<T> = {
  data: T | null;
  error: string | null;
  status: AsyncStatus;
  loading: boolean;
  refetch: () => Promise<void>;
};

/**
 * Reusable async data hook (React hooks only).
 * Exposes loading, error, and data, and supports refetch.
 * Pass a stable `loader` (e.g. wrapped in useCallback) so refetch tracks dependency changes.
 */
export function useAsync<T>(loader: () => Promise<T>): UseAsyncResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<AsyncStatus>("idle");

  const refetch = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const result = await loader();
      setData(result);
      setStatus("success");
    } catch (err) {
      setData(null);
      setStatus("error");
      setError(err instanceof Error ? err.message : "Request failed.");
    }
  }, [loader]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void refetch();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [refetch]);

  return {
    data,
    error,
    status,
    loading: status === "loading" || status === "idle",
    refetch,
  };
}
