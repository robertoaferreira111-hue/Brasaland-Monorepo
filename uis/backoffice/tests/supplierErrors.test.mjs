import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  USER_MESSAGES,
  humanMessageFromPayload,
  messageForHttpFailure,
  normalizeSupplier,
  normalizeSupplierList,
  readJsonSafe,
} from "../supplierErrors.mjs";

describe("humanMessageFromPayload", () => {
  it("returns safe string detail messages", () => {
    assert.equal(
      humanMessageFromPayload({ detail: "Supplier not found" }),
      USER_MESSAGES.httpNotFound,
    );
    assert.equal(
      humanMessageFromPayload({ detail: "Rate updated upstream" }),
      "Rate updated upstream",
    );
  });

  it("blocks sensitive detail content", () => {
    assert.equal(
      humanMessageFromPayload({
        detail: 'Traceback (most recent call last):\nFile "/Users/x/app.py"',
      }),
      null,
    );
  });

  it("formats validation arrays without body/query prefixes", () => {
    const message = humanMessageFromPayload({
      detail: [
        { loc: ["body", "rate_per_unit"], msg: "Input should be greater than 0" },
      ],
    });
    assert.equal(message, "rate_per_unit: Input should be greater than 0");
  });
});

describe("messageForHttpFailure", () => {
  it("prefers safe body detail over status fallbacks", () => {
    assert.equal(
      messageForHttpFailure(404, { detail: "Supplier not found" }),
      USER_MESSAGES.httpNotFound,
    );
  });

  it("never exposes raw HTTP status codes", () => {
    const message = messageForHttpFailure(500, { detail: null });
    assert.equal(message, USER_MESSAGES.httpServer);
    assert.equal(message.includes("500"), false);
    assert.equal(message.includes("HTTP"), false);
  });

  it("uses invalid-input copy for 422 without detail", () => {
    assert.equal(messageForHttpFailure(422, {}), USER_MESSAGES.httpInvalid);
  });
});

describe("readJsonSafe", () => {
  it("returns parsed JSON on success", async () => {
    const response = {
      json: async () => ({ ok: true }),
    };
    const result = await readJsonSafe(response);
    assert.deepEqual(result, { ok: true, data: { ok: true } });
  });

  it("returns a malformed message when JSON parsing fails", async () => {
    const response = {
      json: async () => {
        throw new SyntaxError("Unexpected token");
      },
    };
    const result = await readJsonSafe(response);
    assert.equal(result.ok, false);
    assert.equal(result.message, USER_MESSAGES.malformed);
  });
});

describe("normalizeSupplier / normalizeSupplierList", () => {
  it("fills optional fields safely and keeps required id", () => {
    const supplier = normalizeSupplier({
      id: 7,
      name: "Carnes del Valle",
      status: "suspended",
    });
    assert.equal(supplier.id, 7);
    assert.equal(supplier.contact_email, "");
    assert.deepEqual(supplier.categories, []);
    assert.equal(supplier.status, "suspended");
  });

  it("rejects records without an id instead of inventing success", () => {
    assert.equal(normalizeSupplier({ name: "Missing id" }), null);
  });

  it("rejects non-array list payloads", () => {
    const result = normalizeSupplierList({ suppliers: [] });
    assert.equal(result.ok, false);
    assert.equal(result.message, USER_MESSAGES.invalidList);
  });

  it("keeps valid rows and drops invalid ones from a list", () => {
    const result = normalizeSupplierList([
      { id: 1, name: "Valid" },
      { name: "Invalid" },
    ]);
    assert.equal(result.ok, true);
    assert.equal(result.suppliers.length, 1);
    assert.equal(result.suppliers[0].name, "Valid");
  });
});
