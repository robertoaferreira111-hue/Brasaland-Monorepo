"use client";

import { USER_MESSAGES, type Supplier } from "@/lib/supplierErrors";
import {
  createSupplier,
  listSuppliers,
  updateSupplierRate,
  updateSupplierStatus,
  type NewSupplier,
} from "@/services/suppliers";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import ApiLink from "./ApiLink";

const CATEGORIES = ["carne", "verduras_y_hortalizas", "salsas_y_condimentos", "bebidas", "packaging", "productos_limpieza", "lacteos", "carbon_y_combustible"];
const COUNTRIES = ["Colombia", "USA"];
const CURRENCY: Record<string, string> = { Colombia: "COP", USA: "USD" };

function SupplierRow({ supplier, onUpdated }: { supplier: Supplier; onUpdated: (value: Supplier) => void }) {
  const [rate, setRate] = useState(String(supplier.rate_per_unit));
  const [rateError, setRateError] = useState("");
  const [statusError, setStatusError] = useState("");
  const [busy, setBusy] = useState<"rate" | "status" | null>(null);

  async function saveRate(event?: FormEvent) {
    event?.preventDefault();
    setBusy("rate"); setRateError("");
    try {
      const result = await updateSupplierRate(supplier.id, Number(rate));
      if (result.ok) onUpdated(result.supplier); else setRateError(result.message);
    } finally { setBusy(null); }
  }
  async function toggleStatus() {
    setBusy("status"); setStatusError("");
    try {
      const next = supplier.status === "active" ? "suspended" : "active";
      const result = await updateSupplierStatus(supplier.id, next);
      if (result.ok) onUpdated(result.supplier); else setStatusError(result.message);
    } finally { setBusy(null); }
  }

  return (
    <tr className={supplier.status === "suspended" ? "is-suspended" : ""}>
      <td>{supplier.name || "Unnamed supplier"}</td><td>{supplier.country}</td>
      <td>{supplier.categories.join(", ")}</td>
      <td>
        <form className="rate-form" onSubmit={saveRate}>
          <input type="number" step="any" required value={rate} onChange={(event) => setRate(event.target.value)} aria-label={`rate_per_unit for ${supplier.name || "Unnamed supplier"}`} />
          <button disabled={busy === "rate"}>{busy === "rate" ? "Saving…" : "Update rate"}</button>
          {rateError && <><p className="row-error" role="alert">{rateError}</p><div className="row-recovery"><button type="button" className="button-secondary" onClick={() => void saveRate()}>Try again</button><p className="recovery-hint">If this keeps happening, contact support.</p></div></>}
        </form>
      </td>
      <td>{supplier.currency}</td>
      <td><div className="row-actions">
        <span className={`badge badge-${supplier.status}`}>{supplier.status}</span>
        <button type="button" disabled={busy === "status"} onClick={() => void toggleStatus()}>{busy === "status" ? "Saving…" : supplier.status === "active" ? "Suspend" : "Activate"}</button>
        {statusError && <><p className="row-error" role="alert">{statusError}</p><div className="row-recovery"><button type="button" className="button-secondary" onClick={() => void toggleStatus()}>Try again</button><p className="recovery-hint">If this keeps happening, contact support.</p></div></>}
      </div></td>
      <td>{supplier.contact_email}</td><td>{supplier.notes}</td>
      <td>{supplier.updated_at ? new Date(supplier.updated_at).toLocaleString() : ""}</td>
    </tr>
  );
}

export default function SupplierDirectory() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [country, setCountry] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState("");
  const [formError, setFormError] = useState("");
  const [success, setSuccess] = useState("");
  const [registering, setRegistering] = useState(false);
  const [registerCountry, setRegisterCountry] = useState("Colombia");

  const load = useCallback(async () => {
    setLoading(true); setListError("");
    try {
      const result = await listSuppliers(country, category);
      if (result.ok) setSuppliers(result.suppliers);
      else { setSuppliers([]); setListError(result.message); }
    } catch (error) {
      if (!(error instanceof Error && (error.message === "Session expired" || error.message === "Not authenticated"))) {
        setSuppliers([]); setListError(USER_MESSAGES.network);
      }
    } finally { setLoading(false); }
  }, [country, category]);

  useEffect(() => { void load(); }, [load]);

  function replace(updated: Supplier) {
    setSuppliers((current) => current.some((item) => item.id === updated.id)
      ? current.map((item) => item.id === updated.id ? updated : item)
      : [...current, updated]);
  }

  async function submitSupplier(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setFormError(""); setSuccess("");
    const form = event.currentTarget;
    const data = new FormData(form);
    const categories = data.getAll("categories").map(String);
    if (!categories.length) { setFormError("Select at least one category."); return; }
    const payload: NewSupplier = {
      name: String(data.get("name") || "").trim(), country: registerCountry, categories,
      rate_per_unit: Number(data.get("rate_per_unit")), currency: CURRENCY[registerCountry],
      status: String(data.get("status")) as Supplier["status"],
    };
    const email = String(data.get("contact_email") || "").trim();
    const notes = String(data.get("notes") || "").trim();
    if (email) payload.contact_email = email;
    if (notes) payload.notes = notes;
    setRegistering(true);
    try {
      const result = await createSupplier(payload);
      if (!result.ok) { setFormError(result.message); return; }
      form.reset(); setRegisterCountry("Colombia"); replace(result.supplier);
      setSuccess(`${result.supplier.name || "Supplier"} was registered.`);
      await load();
    } finally { setRegistering(false); }
  }

  const visible = status ? suppliers.filter((supplier) => supplier.status === status) : suppliers;
  return (
    <>
      <section className="panel" aria-labelledby="filters-heading"><h2 id="filters-heading">Filters</h2>
        <form className="filters">
          <label>Country<select value={country} disabled={loading} onChange={(event) => setCountry(event.target.value)}><option value="">All countries</option>{COUNTRIES.map((value) => <option key={value}>{value}</option>)}</select></label>
          <label>Category<select value={category} disabled={loading} onChange={(event) => setCategory(event.target.value)}><option value="">All categories</option>{CATEGORIES.map((value) => <option key={value}>{value}</option>)}</select></label>
          <label>Status<select value={status} disabled={loading} onChange={(event) => setStatus(event.target.value)}><option value="">All statuses</option><option value="active">active</option><option value="suspended">suspended</option></select></label>
        </form>
      </section>
      <p className="status-line" role="status">{loading ? "Loading suppliers…" : !listError ? `${visible.length} supplier${visible.length === 1 ? "" : "s"} shown.` : ""}</p>
      {listError && <div className="error-panel"><p className="message message-error" role="alert">{listError}</p><div className="error-actions"><button onClick={() => void load()}>Try again</button><ApiLink className="text-link" href="/">Back to home</ApiLink><p className="recovery-hint">If this keeps happening, contact support.</p></div></div>}
      {!loading && !listError && !visible.length && <p className="message">No suppliers match these filters.</p>}
      {!!visible.length && <div className="table-wrap" aria-busy={loading}><table><caption className="sr-only">Brasaland suppliers</caption>
        <thead><tr>{["name","country","categories","rate_per_unit","currency","status","contact_email","notes","updated_at"].map((heading) => <th key={heading} scope="col">{heading}</th>)}</tr></thead>
        <tbody>{visible.map((supplier) => <SupplierRow key={supplier.id} supplier={supplier} onUpdated={(updated) => { replace(updated); setSuccess("Supplier updated."); }} />)}</tbody>
      </table></div>}
      <section className="panel" aria-labelledby="register-heading"><h2 id="register-heading">Register a supplier</h2>
        <form className="register-form" noValidate onSubmit={submitSupplier}>
          <label>Supplier trade name<input name="name" autoComplete="organization" required /></label>
          <label>Operating country<select name="country" value={registerCountry} onChange={(event) => setRegisterCountry(event.target.value)}>{COUNTRIES.map((value) => <option key={value}>{value}</option>)}</select></label>
          <fieldset><legend>Product categories</legend><div className="choices">{CATEGORIES.map((value) => <label key={value}><input type="checkbox" name="categories" value={value} />{value}</label>)}</div></fieldset>
          <label>Current rate per unit<input name="rate_per_unit" type="number" step="any" required /></label>
          <label>Currency<input name="currency" value={CURRENCY[registerCountry]} readOnly /></label>
          <label>Status<select name="status" defaultValue="active"><option value="active">active</option><option value="suspended">suspended</option></select></label>
          <label>Supplier contact email<input name="contact_email" type="text" autoComplete="email" /></label>
          <label className="span-2">Internal procurement team notes<textarea name="notes" rows={3} /></label>
          <div className="form-actions span-2"><button disabled={registering}>{registering ? "Registering…" : "Register supplier"}</button></div>
        </form>
        {formError && <><p className="message message-error" role="alert">{formError}</p><div className="error-actions"><p className="recovery-hint">Correct the form or try again. If this keeps happening, contact support.</p></div></>}
        {success && <p className="message message-success" role="status">{success}</p>}
      </section>
    </>
  );
}
