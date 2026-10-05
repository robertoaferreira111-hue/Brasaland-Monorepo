import type { CandidateCreate } from "@/types/candidate";

export type FormErrors = Partial<Record<keyof CandidateCreate, string>>;

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateCandidateForm(
  values: CandidateCreate,
): FormErrors {
  const errors: FormErrors = {};

  if (!values.full_name.trim()) {
    errors.full_name = "Full name is required.";
  }

  if (!values.email.trim()) {
    errors.email = "Email is required.";
  } else if (!EMAIL_PATTERN.test(values.email.trim())) {
    errors.email = "Enter a valid email address.";
  }

  if (!values.phone.trim()) {
    errors.phone = "Phone is required.";
  }

  if (!values.position.trim()) {
    errors.position = "Position is required.";
  }

  if (
    values.experience_years === undefined ||
    values.experience_years === null ||
    Number.isNaN(Number(values.experience_years))
  ) {
    errors.experience_years = "Years of experience is required.";
  } else if (Number(values.experience_years) < 0) {
    errors.experience_years = "Years of experience cannot be negative.";
  }

  if (values.linkedin_url?.trim()) {
    try {
      new URL(values.linkedin_url.trim());
    } catch {
      errors.linkedin_url = "Enter a valid LinkedIn URL.";
    }
  }

  if (values.cv_url?.trim()) {
    try {
      new URL(values.cv_url.trim());
    } catch {
      errors.cv_url = "Enter a valid CV URL.";
    }
  }

  return errors;
}

export function hasFormErrors(errors: FormErrors): boolean {
  return Object.keys(errors).length > 0;
}

export function toCandidatePayload(values: CandidateCreate): CandidateCreate {
  return {
    full_name: values.full_name.trim(),
    email: values.email.trim(),
    phone: values.phone.trim(),
    position: values.position.trim(),
    experience_years: Number(values.experience_years),
    linkedin_url: values.linkedin_url?.trim() || null,
    cv_url: values.cv_url?.trim() || null,
  };
}
