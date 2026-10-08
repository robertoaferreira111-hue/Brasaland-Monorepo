export type Profile = {
  email: string;
  name: string;
  phone: string;
  address: string;
};

export const NAME_ERROR = "Enter your name";
export const PHONE_ERROR = "Enter a phone number";
export const ADDRESS_ERROR = "Enter your address";

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function pickString(record: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string") {
      return value.trim();
    }
  }
  return "";
}

export function readProfile(data: unknown): Profile {
  const record = asRecord(data);
  if (!record) {
    return { email: "", name: "", phone: "", address: "" };
  }
  const nested =
    asRecord(record.user) ?? asRecord(record.profile) ?? asRecord(record.data);
  const email =
    pickString(record, ["email"]) ||
    (nested ? pickString(nested, ["email"]) : "");
  const contact = nested ?? record;
  return {
    email,
    name:
      pickString(contact, ["name", "full_name", "fullName"]) ||
      pickString(record, ["name", "full_name", "fullName"]),
    phone:
      pickString(contact, ["phone", "phone_number", "phoneNumber"]) ||
      pickString(record, ["phone", "phone_number", "phoneNumber"]),
    address:
      pickString(contact, ["address"]) || pickString(record, ["address"]),
  };
}

export function nameFieldError(value: string): string {
  return value.trim().length > 0 ? "" : NAME_ERROR;
}

export function phoneFieldError(value: string): string {
  return value.trim().length > 0 ? "" : PHONE_ERROR;
}

export function addressFieldError(value: string): string {
  return value.trim().length > 0 ? "" : ADDRESS_ERROR;
}

export function profileUpdatePayload(input: {
  name: string;
  phone: string;
  address: string;
}): { name: string; phone: string; address: string } | null {
  if (
    nameFieldError(input.name) ||
    phoneFieldError(input.phone) ||
    addressFieldError(input.address)
  ) {
    return null;
  }
  return {
    name: input.name.trim(),
    phone: input.phone.trim(),
    address: input.address.trim(),
  };
}

export function mergeSavedProfile(
  saved: Profile,
  submitted: { name: string; phone: string; address: string },
  previousEmail: string,
): Profile {
  return {
    email: saved.email || previousEmail,
    name: saved.name || submitted.name,
    phone: saved.phone || submitted.phone,
    address: saved.address || submitted.address,
  };
}
