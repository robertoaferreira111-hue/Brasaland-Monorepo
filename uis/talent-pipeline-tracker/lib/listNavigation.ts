import { ApiError } from "@/types/api";

const LIST_QUERY_KEY = "tpt-list-query";
export const LIST_QUERY_EVENT = "tpt-list-query";

/** Remember the candidate list query string so detail "back" links can restore it. */
export function rememberListQuery(query: string): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(LIST_QUERY_KEY, query);
  window.dispatchEvent(new Event(LIST_QUERY_EVENT));
}

/** Build `/` or `/?status=…` from the last remembered list query. */
export function getListHref(): string {
  if (typeof window === "undefined") return "/";
  const query = sessionStorage.getItem(LIST_QUERY_KEY);
  return query ? `/?${query}` : "/";
}

export function subscribeListHref(onStoreChange: () => void): () => void {
  if (typeof window === "undefined") return () => undefined;
  window.addEventListener(LIST_QUERY_EVENT, onStoreChange);
  return () => window.removeEventListener(LIST_QUERY_EVENT, onStoreChange);
}

export function isNotFoundError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}
