import { withoutSecret } from "../lib/credentials";

describe("withoutSecret (FE-019)", () => {
  test("keeps a message that does not contain the secret", () => {
    expect(withoutSecret("Incorrect email or password", "hunter2")).toBe(
      "Incorrect email or password",
    );
  });

  test("replaces a message that repeats the secret", () => {
    expect(withoutSecret("failed for hunter2", "hunter2")).toBe(
      "That request failed. Check the details and try again.",
    );
  });
});
