"use client";

import { useCallback, useEffect, useRef, useState } from "react";

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
 * In-flight responses from older loaders are ignored so rapid filter changes cannot show stale data.
 */
export function useAsync<T>(loader: () => Promise<T>): UseAsyncResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<AsyncStatus>("idle");
  const requestIdRef = useRef(0);

  const refetch = useCallback(async () => {
    const requestId = ++requestIdRef.current;
    setStatus("loading");
    setError(null);
    setData(null);
    try {
      const result = await loader();
      if (requestId !== requestIdRef.current) return;
      setData(result);
      setStatus("success");
    } catch (err) {
      if (requestId !== requestIdRef.current) return;
      setData(null);
      setStatus("error");
      setError(err instanceof Error ? err.message : "Request failed.");
    }
  }, [loader]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void refetch();
    }, 0);
    return () => {
      window.clearTimeout(timer);
      // Invalidate any in-flight request when deps change or unmount.
      requestIdRef.current += 1;
    };
  }, [refetch]);

  return {
    data,
    error,
    status,
    loading: status === "loading" || status === "idle",
    refetch,
  };
}
