import { apiFetch } from "@/lib/session";
import {
  USER_MESSAGES,
  messageForHttpFailure,
  normalizeSupplier,
  normalizeSupplierList,
  readJsonSafe,
  type Supplier,
} from "@/lib/supplierErrors";

export async function listSuppliers(country: string, category: string) {
  const params = new URLSearchParams();
  if (country) params.set("country", country);
  if (category) params.set("category", category);
  const response = await apiFetch(`/suppliers${params.size ? `?${params}` : ""}`);
  if (!response.ok) {
    const parsed = await readJsonSafe(response);
    return { ok: false as const, message: parsed.ok ? messageForHttpFailure(response.status, parsed.data) : parsed.message };
  }
  const parsed = await readJsonSafe(response);
  if (!parsed.ok) return { ok: false as const, message: parsed.message };
  const normalized = normalizeSupplierList(parsed.data);
  return normalized.ok
    ? { ok: true as const, suppliers: normalized.suppliers }
    : { ok: false as const, message: normalized.message };
}

async function mutate(path: string, method: "POST" | "PATCH", body: unknown) {
  try {
    const response = await apiFetch(path, { method, body: JSON.stringify(body) });
    if (!response.ok) {
      const parsed = await readJsonSafe(response);
      return { ok: false as const, message: parsed.ok ? messageForHttpFailure(response.status, parsed.data) : parsed.message };
    }
    const parsed = await readJsonSafe(response);
    if (!parsed.ok) return { ok: false as const, message: parsed.message };
    const supplier = normalizeSupplier(parsed.data);
    return supplier
      ? { ok: true as const, supplier }
      : { ok: false as const, message: USER_MESSAGES.malformed };
  } catch (error) {
    if (error instanceof Error && (error.message === "Session expired" || error.message === "Not authenticated")) throw error;
    return { ok: false as const, message: USER_MESSAGES.network };
  }
}

export type NewSupplier = Omit<Supplier, "id" | "updated_at" | "contact_email" | "notes"> & {
  contact_email?: string;
  notes?: string;
};

export const createSupplier = (supplier: NewSupplier) => mutate("/suppliers", "POST", supplier);
export const updateSupplierRate = (id: Supplier["id"], rate: number) =>
  mutate(`/suppliers/${id}/rate`, "PATCH", { rate_per_unit: rate });
export const updateSupplierStatus = (id: Supplier["id"], status: Supplier["status"]) =>
  mutate(`/suppliers/${id}/status`, "PATCH", { status });
