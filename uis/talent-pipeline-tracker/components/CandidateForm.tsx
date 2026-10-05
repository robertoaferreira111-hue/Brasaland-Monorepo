"use client";

import { FormEvent, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { FeedbackBanner } from "@/components/FeedbackBanner";
import { createRecord, updateRecord } from "@/lib/api";
import {
  hasFormErrors,
  toCandidatePayload,
  validateCandidateForm,
  type FormErrors,
} from "@/lib/validation";
import type { Candidate, CandidateCreate } from "@/types/candidate";

type CandidateFormProps = {
  mode: "create" | "edit";
  initialValues?: Candidate;
};

const emptyValues: CandidateCreate = {
  full_name: "",
  email: "",
  phone: "",
  position: "Executive Assistant",
  experience_years: 0,
  linkedin_url: "",
  cv_url: "",
};

export function CandidateForm({ mode, initialValues }: CandidateFormProps) {
  const router = useRouter();
  const [values, setValues] = useState<CandidateCreate>(() =>
    initialValues
      ? {
          full_name: initialValues.full_name,
          email: initialValues.email,
          phone: initialValues.phone,
          position: initialValues.position,
          experience_years: initialValues.experience_years,
          linkedin_url: initialValues.linkedin_url ?? "",
          cv_url: initialValues.cv_url ?? "",
        }
      : emptyValues,
  );
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function updateField<K extends keyof CandidateCreate>(
    key: K,
    value: CandidateCreate[K],
  ) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSuccess(null);
    setError(null);

    const nextErrors = validateCandidateForm(values);
    setErrors(nextErrors);
    if (hasFormErrors(nextErrors)) {
      setError("Please fix the highlighted fields before submitting.");
      return;
    }

    const payload = toCandidatePayload(values);
    setSubmitting(true);
    try {
      if (mode === "create") {
        const created = await createRecord(payload);
        setSuccess("Candidate registered successfully.");
        router.push(`/candidates/${created.id}`);
      } else if (initialValues) {
        const updated = await updateRecord(initialValues.id, payload);
        setSuccess("Candidate updated successfully.");
        router.push(`/candidates/${updated.id}`);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : mode === "create"
            ? "Failed to register candidate."
            : "Failed to update candidate.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="grid max-w-2xl gap-4" noValidate>
      {error && <FeedbackBanner tone="error" message={error} />}
      {success && <FeedbackBanner tone="success" message={success} />}

      <Field
        label="Full name"
        error={errors.full_name}
        required
      >
        <input
          value={values.full_name}
          onChange={(event) => updateField("full_name", event.target.value)}
          className={inputClass(Boolean(errors.full_name))}
        />
      </Field>

      <Field label="Email" error={errors.email} required>
        <input
          type="email"
          value={values.email}
          onChange={(event) => updateField("email", event.target.value)}
          className={inputClass(Boolean(errors.email))}
        />
      </Field>

      <Field label="Phone" error={errors.phone} required>
        <input
          value={values.phone}
          onChange={(event) => updateField("phone", event.target.value)}
          className={inputClass(Boolean(errors.phone))}
        />
      </Field>

      <Field label="Position" error={errors.position} required>
        <input
          value={values.position}
          onChange={(event) => updateField("position", event.target.value)}
          className={inputClass(Boolean(errors.position))}
        />
      </Field>

      <Field
        label="Years of experience"
        error={errors.experience_years}
        required
      >
        <input
          type="number"
          min={0}
          step={0.5}
          value={values.experience_years}
          onChange={(event) =>
            updateField("experience_years", Number(event.target.value))
          }
          className={inputClass(Boolean(errors.experience_years))}
        />
      </Field>

      <Field label="LinkedIn URL" error={errors.linkedin_url}>
        <input
          type="url"
          value={values.linkedin_url ?? ""}
          onChange={(event) => updateField("linkedin_url", event.target.value)}
          className={inputClass(Boolean(errors.linkedin_url))}
          placeholder="https://linkedin.com/in/…"
        />
      </Field>

      <Field label="CV URL" error={errors.cv_url}>
        <input
          type="url"
          value={values.cv_url ?? ""}
          onChange={(event) => updateField("cv_url", event.target.value)}
          className={inputClass(Boolean(errors.cv_url))}
          placeholder="https://…"
        />
      </Field>

      <div className="flex flex-wrap gap-3 pt-2">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting
            ? mode === "create"
              ? "Registering…"
              : "Saving…"
            : mode === "create"
              ? "Register candidate"
              : "Save changes"}
        </button>
        <button
          type="button"
          onClick={() => router.back()}
          className="rounded-md border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--ink)]"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

function Field({
  label,
  error,
  required,
  children,
}: {
  label: string;
  error?: string;
  required?: boolean;
  children: ReactNode;
}) {
  return (
    <label className="grid gap-1 text-sm">
      <span className="font-medium text-[var(--ink)]">
        {label}
        {required ? " *" : ""}
      </span>
      {children}
      {error && <span className="text-xs text-red-700">{error}</span>}
    </label>
  );
}

function inputClass(hasError: boolean): string {
  return `rounded-md border px-3 py-2 text-[var(--ink)] outline-none ring-[var(--accent)] focus:ring-2 ${
    hasError
      ? "border-red-400 bg-red-50"
      : "border-[var(--border)] bg-white"
  }`;
}
