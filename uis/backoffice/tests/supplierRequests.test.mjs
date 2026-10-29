import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { USER_MESSAGES } from "../supplierErrors.mjs";
import {
  requestJsonMutation,
  requestSupplierList,
  withLoadingState,
} from "../supplierRequests.mjs";

function jsonResponse(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  };
}

function textResponse(status, text) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => {
      throw new SyntaxError(text);
    },
  };
}

describe("requestSupplierList", () => {
  it("returns fulfilled suppliers on success", async () => {
    const result = await requestSupplierList("/suppliers", async () =>
      jsonResponse(200, [{ id: 1, name: "A", status: "active" }]),
    );
    assert.equal(result.status, "fulfilled");
    assert.equal(result.suppliers.length, 1);
    assert.equal(result.suppliers[0].name, "A");
  });

  it("maps network failures to a rejected user message", async () => {
    const result = await requestSupplierList("/suppliers", async () => {
      throw new TypeError("Failed to fetch");
    });
    assert.equal(result.status, "rejected");
    assert.equal(result.message, USER_MESSAGES.network);
    assert.equal(result.message.includes("127.0.0.1"), false);
  });

  it("maps HTTP errors without exposing status codes", async () => {
    const result = await requestSupplierList("/suppliers", async () =>
      jsonResponse(500, { detail: "Internal boom" }),
    );
    assert.equal(result.status, "rejected");
    assert.equal(result.message, "Internal boom");
    assert.equal(result.message.includes("500"), false);
  });

  it("maps malformed JSON to a rejected message", async () => {
    const result = await requestSupplierList("/suppliers", async () =>
      textResponse(200, "not-json"),
    );
    assert.equal(result.status, "rejected");
    assert.equal(result.message, USER_MESSAGES.malformed);
  });

  it("rejects non-array payloads", async () => {
    const result = await requestSupplierList("/suppliers", async () =>
      jsonResponse(200, { unexpected: true }),
    );
    assert.equal(result.status, "rejected");
    assert.equal(result.message, USER_MESSAGES.invalidList);
  });
});

describe("requestJsonMutation", () => {
  it("returns fulfilled normalized supplier data", async () => {
    const result = await requestJsonMutation(
      "/suppliers/1/rate",
      { method: "PATCH" },
      async () =>
        jsonResponse(200, {
          id: 1,
          name: "A",
          rate_per_unit: 12,
          status: "active",
        }),
    );
    assert.equal(result.status, "fulfilled");
    assert.equal(result.data.rate_per_unit, 12);
  });

  it("returns rejected on network errors", async () => {
    const result = await requestJsonMutation(
      "/suppliers",
      { method: "POST" },
      async () => {
        throw new Error("offline");
      },
    );
    assert.equal(result.status, "rejected");
    assert.equal(result.message, USER_MESSAGES.network);
  });

  it("returns rejected on HTTP validation errors", async () => {
    const result = await requestJsonMutation(
      "/suppliers",
      { method: "POST" },
      async () =>
        jsonResponse(422, {
          detail: [
            {
              loc: ["body", "name"],
              msg: "Field required",
            },
          ],
        }),
    );
    assert.equal(result.status, "rejected");
    assert.equal(result.message, "name: Field required");
  });
});

describe("withLoadingState", () => {
  it("clears loading after success", async () => {
    const states = [];
    const result = await withLoadingState(
      (value) => states.push(value),
      async () => "ok",
    );
    assert.equal(result, "ok");
    assert.deepEqual(states, [true, false]);
  });

  it("clears loading after rejection", async () => {
    const states = [];
    await assert.rejects(
      () =>
        withLoadingState(
          (value) => states.push(value),
          async () => {
            throw new Error("fail");
          },
        ),
      /fail/,
    );
    assert.deepEqual(states, [true, false]);
  });

  it("supports retry by running a fresh loading lifecycle", async () => {
    const states = [];
    let attempts = 0;
    const run = () =>
      withLoadingState(
        (value) => states.push(value),
        async () => {
          attempts += 1;
          if (attempts === 1) {
            return { status: "rejected" };
          }
          return { status: "fulfilled" };
        },
      );

    assert.equal((await run()).status, "rejected");
    assert.equal((await run()).status, "fulfilled");
    assert.equal(attempts, 2);
    assert.deepEqual(states, [true, false, true, false]);
  });
});
