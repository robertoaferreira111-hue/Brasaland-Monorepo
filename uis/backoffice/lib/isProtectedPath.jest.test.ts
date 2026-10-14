import { isProtectedPath } from "./routes";

describe("isProtectedPath", () => {
  test("protects the account page and paths under it", () => {
    expect(isProtectedPath("/account")).toBe(true);
    expect(isProtectedPath("/account/settings")).toBe(true);
  });

  test("does not protect the public sign-in paths", () => {
    expect(isProtectedPath("/login")).toBe(false);
    expect(isProtectedPath("/register")).toBe(false);
    expect(isProtectedPath("/accounts")).toBe(false);
  });
});
