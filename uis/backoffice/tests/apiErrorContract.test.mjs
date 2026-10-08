/**
 * Cross-layer contract: backoffice understanding of services/api error bodies.
 * Keep these strings aligned with services/api/app/errors.py and 404 detail text.
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  BACKEND_SAFE_DETAILS,
  USER_MESSAGES,
  humanMessageFromPayload,
  messageForHttpFailure,
} from "../supplierErrors.mjs";
import { requestSupplierList } from "../supplierRequests.mjs";

describe("API error contract compatibility", () => {
  it("maps known backend 500 detail strings to actionable UI copy", () => {
    assert.equal(
      humanMessageFromPayload({
        detail: BACKEND_SAFE_DETAILS.storageUnavailable,
      }),
      USER_MESSAGES.storageUnavailable,
    );
    assert.equal(
      humanMessageFromPayload({
        detail: BACKEND_SAFE_DETAILS.storedDataInvalid,
      }),
      USER_MESSAGES.storedDataInvalid,
    );
    assert.equal(
      humanMessageFromPayload({
        detail: BACKEND_SAFE_DETAILS.unexpectedError,
      }),
      USER_MESSAGES.unexpectedServer,
    );
  });

  it("maps backend 404 detail to the not-found recovery message", () => {
    assert.equal(
      messageForHttpFailure(404, { detail: BACKEND_SAFE_DETAILS.notFound }),
      USER_MESSAGES.httpNotFound,
    );
  });

  it("keeps FastAPI 422 detail arrays readable for the UI", () => {
    const message = messageForHttpFailure(422, {
      detail: [
        {
          loc: ["body", "rate_per_unit"],
          msg: "Input should be greater than 0",
        },
      ],
    });
    assert.equal(message, "rate_per_unit: Input should be greater than 0");
  });

  it("list loader surfaces mapped storage failures without paths or status codes", async () => {
    const result = await requestSupplierList("/suppliers", async () => ({
      ok: false,
      status: 500,
      json: async () => ({
        detail: BACKEND_SAFE_DETAILS.storageUnavailable,
      }),
    }));
    assert.equal(result.status, "rejected");
    assert.equal(result.message, USER_MESSAGES.storageUnavailable);
    assert.equal(result.message.includes("500"), false);
    assert.equal(result.message.includes("suppliers.json"), false);
    assert.equal(result.message.includes("/Users/"), false);
  });
});
