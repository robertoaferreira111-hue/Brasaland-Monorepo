import { SessionExpiredError, toErrorMessage } from "./api";

describe("toErrorMessage", () => {
  test("returns the message from an ordinary error", () => {
    expect(toErrorMessage(new Error("Incorrect email or password"))).toBe(
      "Incorrect email or password",
    );
  });

  test("hides a session-expiry error and explains a network failure", () => {
    expect(toErrorMessage(new SessionExpiredError())).toBe("");
    expect(toErrorMessage(new TypeError("fetch failed"))).toBe(
      "Could not reach the Brasaland API. Check that it is running.",
    );
    expect(toErrorMessage("nope")).toBe("Something went wrong.");
  });
});