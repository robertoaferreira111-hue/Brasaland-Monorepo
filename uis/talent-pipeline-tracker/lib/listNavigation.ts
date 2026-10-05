/**
 * List ↔ detail return navigation.
 * Authoritative mechanism: the `return` query param on detail URLs
 * (e.g. `/candidates/:id?return=status%3Dreceived%26page%3D2`).
 * sessionStorage is not used.
 */

/** Build a detail href that carries the current list query for later restoration. */
export function buildDetailHref(candidateId: string, listQuery: string): string {
  if (!listQuery) return `/candidates/${candidateId}`;
  return `/candidates/${candidateId}?return=${encodeURIComponent(listQuery)}`;
}

/** Resolve the list href from a detail page `return` query value. */
export function listHrefFromReturnParam(returnQuery: string | null): string {
  if (returnQuery === null) return "/";
  return returnQuery ? `/?${returnQuery}` : "/";
}
