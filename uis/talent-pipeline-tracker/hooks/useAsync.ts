"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/types/api";

type AsyncStatus = "idle" | "loading" | "success" | "error";

export type RefetchOptions = {
  /** When true, previous data stays visible while the new request runs. */
  keepPreviousData?: boolean;
};

export type UseAsyncResult<T> = {
  data: T | null;
  error: string | null;
  errorStatus: number | null;
  status: AsyncStatus;
  loading: boolean;
  refetch: (options?: RefetchOptions) => Promise<T | null>;
};

/**
 * Reusable async data hook (React hooks only).
 * In-flight responses from older requests are ignored (race guard).
 * `refetch({ keepPreviousData: true })` supports post-mutation refresh without blanking the UI.
 */
export function useAsync<T>(loader: () => Promise<T>): UseAsyncResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [status, setStatus] = useState<AsyncStatus>("idle");
  const requestIdRef = useRef(0);

  const refetch = useCallback(async (options?: RefetchOptions) => {
    const requestId = ++requestIdRef.current;
    setStatus("loading");
    setError(null);
    setErrorStatus(null);
    if (!options?.keepPreviousData) {
      setData(null);
    }
    try {
      const result = await loader();
      if (requestId !== requestIdRef.current) return null;
      setData(result);
      setStatus("success");
      return result;
    } catch (err) {
      if (requestId !== requestIdRef.current) return null;
      if (!options?.keepPreviousData) {
        setData(null);
      }
      setStatus("error");
      setError(err instanceof Error ? err.message : "Request failed.");
      setErrorStatus(err instanceof ApiError ? err.status : null);
      return null;
    }
  }, [loader]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void refetch();
    }, 0);
    return () => {
      window.clearTimeout(timer);
      requestIdRef.current += 1;
    };
  }, [refetch]);

  return {
    data,
    error,
    errorStatus,
    status,
    loading: status === "loading" || status === "idle",
    refetch,
  };
}
