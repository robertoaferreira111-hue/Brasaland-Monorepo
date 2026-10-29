/**
 * Dev-only parity checks for Brasa Points validation (ported from validation.js).
 * Run: npm run verify:validation
 */

import assert from "node:assert/strict";
import {
  emptyValues,
  isAtLeast18,
  messageFor,
  validateAll,
  type BrasaPointsValues,
} from "../lib/brasaPoints";

function base(overrides: Partial<BrasaPointsValues> = {}): BrasaPointsValues {
  return {
    ...emptyValues(),
    "full-name": "Lucia Fernandez",
    email: "lucia@brasaland.com",
    phone: "+57 300 123 4567",
    country: "Colombia",
    city: "Medellín",
    source: "Social media",
    "date-of-birth": "1990-01-15",
    "accept-terms": true,
    ...overrides,
  };
}

assert.equal(messageFor("full-name", base({ "full-name": "Lucia" })), "Enter your full name (first and last name)");
assert.equal(messageFor("full-name", base()), "");

assert.equal(messageFor("email", base({ email: "bad" })), "Enter a valid email (example: name@email.com)");
assert.equal(messageFor("email", base()), "");

// Phone waits for country selection before enforcing country-code format.
assert.equal(messageFor("phone", base({ country: "", phone: "3001234567" })), "");
assert.equal(
  messageFor("phone", base({ country: "Colombia", phone: "3001234567" })),
  "Phone must include country code (example: +57 300 123 4567 or +1 305 123 4567)",
);
assert.equal(messageFor("phone", base({ country: "Colombia", phone: "+57 300 123 4567" })), "");
assert.equal(messageFor("phone", base({ country: "United States", phone: "+1 305 123 4567", city: "Miami" })), "");

assert.equal(isAtLeast18("2015-01-01", new Date("2026-10-29")), false);
assert.equal(isAtLeast18("2000-01-01", new Date("2026-10-29")), true);

const invalid = validateAll(emptyValues());
assert.equal(invalid.firstInvalid, "full-name");
assert.ok(invalid.errors.country);
assert.ok(invalid.errors["accept-terms"]);

const valid = validateAll(base());
assert.equal(valid.firstInvalid, "");
assert.deepEqual(valid.errors, {});

console.log("WEBSITE_VALIDATION_VERIFY_OK");
