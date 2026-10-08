import {
  USER_MESSAGES,
  messageForHttpFailure,
  normalizeSupplier,
  normalizeSupplierList,
  readJsonSafe,
} from "./supplierErrors.mjs";

/**
 * Load and normalize the supplier list. Always settles to fulfilled or rejected.
 */
export async function requestSupplierList(url, fetchImpl = fetch) {
  try {
    const response = await fetchImpl(url);
    if (!response.ok) {
      const parsed = await readJsonSafe(response);
      const message = parsed.ok
        ? messageForHttpFailure(response.status, parsed.data)
        : parsed.message;
      return { status: "rejected", message, suppliers: [] };
    }

    const parsed = await readJsonSafe(response);
    if (!parsed.ok) {
      return { status: "rejected", message: parsed.message, suppliers: [] };
    }

    const normalized = normalizeSupplierList(parsed.data);
    if (!normalized.ok) {
      return {
        status: "rejected",
        message: normalized.message,
        suppliers: [],
      };
    }

    return {
      status: "fulfilled",
      message: "",
      suppliers: normalized.suppliers,
    };
  } catch {
    return {
      status: "rejected",
      message: USER_MESSAGES.network,
      suppliers: [],
    };
  }
}

/**
 * PATCH helper that returns fulfilled/rejected without throwing.
 */
export async function requestJsonMutation(url, init, fetchImpl = fetch) {
  try {
    const response = await fetchImpl(url, init);
    if (!response.ok) {
      const parsed = await readJsonSafe(response);
      const message = parsed.ok
        ? messageForHttpFailure(response.status, parsed.data)
        : parsed.message;
      return { status: "rejected", message, data: null };
    }

    const parsed = await readJsonSafe(response);
    if (!parsed.ok) {
      return { status: "rejected", message: parsed.message, data: null };
    }

    const supplier = normalizeSupplier(parsed.data);
    if (!supplier) {
      return {
        status: "rejected",
        message: USER_MESSAGES.malformed,
        data: null,
      };
    }

    return { status: "fulfilled", message: "", data: supplier };
  } catch {
    return {
      status: "rejected",
      message: USER_MESSAGES.network,
      data: null,
    };
  }
}

/**
 * Tiny loading-state helper used to prove finally-style cleanup in tests.
 */
export function withLoadingState(setLoading, operation) {
  setLoading(true);
  return Promise.resolve()
    .then(() => operation())
    .finally(() => {
      setLoading(false);
    });
}
