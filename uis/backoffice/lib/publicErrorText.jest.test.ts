import { publicErrorText } from "./errors";

describe("publicErrorText", () => {
  test("returns the API detail when it is safe to show", () => {
    expect(
      publicErrorText(401, JSON.stringify({ detail: "Incorrect email or password" })),
    ).toBe("Incorrect email or password");
  });

  test("hides an empty body, a token-shaped body, and text that is not JSON", () => {
    expect(publicErrorText(401, "   ")).toBe("Request failed (401)");
    expect(
      publicErrorText(401, "aaaa.bbbb.cccc"),
    ).toBe("Request failed (401)");
    expect(publicErrorText(401, "Bearer live-token")).toBe("Request failed (401)");
    expect(publicErrorText(500, "not-json")).toBe("Request failed (500)");
  });
});
