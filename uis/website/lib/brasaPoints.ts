/** Brasa Points registration options and pure validation (ported from validation.js). */

export const CITIES: Record<string, string[]> = {
  Colombia: ["Medellín", "Bogotá", "Cali"],
  "United States": ["Miami", "Orlando"],
};

export const LOCATIONS: Record<string, string[]> = {
  Medellín: [
    "Brasaland El Poblado",
    "Brasaland Laureles",
    "Brasaland Envigado",
    "Brasaland Sabaneta",
  ],
  Bogotá: ["Brasaland Usaquén", "Brasaland Chapinero", "Brasaland Zona Rosa"],
  Cali: ["Brasaland Granada", "Brasaland Ciudad Jardín", "Brasaland Unicentro"],
  Miami: ["Brasaland Brickell", "Brasaland Coral Gables"],
  Orlando: ["Brasaland Downtown", "Brasaland International Drive"],
};

export const SOURCES = [
  "Social media",
  "Recommendation",
  "Walked by",
  "Internet search",
  "Other",
] as const;

export const DIETARY_OPTIONS = [
  "No restrictions",
  "Vegetarian",
  "Gluten-free",
  "Other",
] as const;

export const ERRORS = {
  "full-name": "Enter your full name (first and last name)",
  email: "Enter a valid email (example: name@email.com)",
  phone:
    "Phone must include country code (example: +57 300 123 4567 or +1 305 123 4567)",
  country: "Select your country",
  city: "Select your city",
  source: "Tell us how you found Brasaland",
  "date-of-birth": "You must be 18 or older to register for Brasa Points",
  "accept-terms": "You must accept the Brasa Points program terms to continue",
} as const;

export type FieldId = keyof typeof ERRORS;

export const FIELD_ORDER: FieldId[] = [
  "full-name",
  "email",
  "phone",
  "country",
  "city",
  "source",
  "date-of-birth",
  "accept-terms",
];

export type BrasaPointsValues = {
  "full-name": string;
  email: string;
  phone: string;
  country: string;
  city: string;
  "favorite-location": string;
  dietary: string[];
  source: string;
  "date-of-birth": string;
  "accept-terms": boolean;
  offers: boolean;
};

export function isAtLeast18(isoDate: string, today = new Date()): boolean {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoDate);
  if (!match) return false;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const birth = new Date(year, month - 1, day);
  if (
    birth.getFullYear() !== year ||
    birth.getMonth() !== month - 1 ||
    birth.getDate() !== day
  ) {
    return false;
  }
  const cutoff = new Date(today.getFullYear() - 18, today.getMonth(), today.getDate());
  return birth <= cutoff;
}

/**
 * Validate one field. Phone checks wait until country is Colombia or United States
 * (empty phone still fails once a country is chosen).
 */
export function messageFor(id: FieldId, values: BrasaPointsValues): string {
  const country = values.country;
  const city = values.city;

  if (id === "full-name") {
    const words = values["full-name"].trim().split(/\s+/).filter(Boolean);
    return words.length >= 2 ? "" : ERRORS[id];
  }

  if (id === "email") {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email.trim())
      ? ""
      : ERRORS[id];
  }

  if (id === "phone") {
    const compact = values.phone.trim().replace(/[\s()-]/g, "");
    if (!compact) return ERRORS[id];
    if (country !== "Colombia" && country !== "United States") return "";
    const ok =
      country === "Colombia"
        ? /^\+57\d{8,12}$/.test(compact)
        : /^\+1\d{10}$/.test(compact);
    return ok ? "" : ERRORS[id];
  }

  if (id === "country") {
    return country === "Colombia" || country === "United States" ? "" : ERRORS[id];
  }

  if (id === "city") {
    const cities = CITIES[country] || [];
    return city && cities.includes(city) ? "" : ERRORS[id];
  }

  if (id === "source") {
    return (SOURCES as readonly string[]).includes(values.source) ? "" : ERRORS[id];
  }

  if (id === "date-of-birth") {
    return isAtLeast18(values["date-of-birth"]) ? "" : ERRORS[id];
  }

  if (id === "accept-terms") {
    return values["accept-terms"] ? "" : ERRORS[id];
  }

  return "";
}

export function validateAll(values: BrasaPointsValues): {
  errors: Partial<Record<FieldId, string>>;
  firstInvalid: FieldId | "";
} {
  const errors: Partial<Record<FieldId, string>> = {};
  let firstInvalid: FieldId | "" = "";
  for (const id of FIELD_ORDER) {
    const message = messageFor(id, values);
    if (message) {
      errors[id] = message;
      if (!firstInvalid) firstInvalid = id;
    }
  }
  return { errors, firstInvalid };
}

export const emptyValues = (): BrasaPointsValues => ({
  "full-name": "",
  email: "",
  phone: "",
  country: "",
  city: "",
  "favorite-location": "",
  dietary: [],
  source: "",
  "date-of-birth": "",
  "accept-terms": false,
  offers: false,
});
