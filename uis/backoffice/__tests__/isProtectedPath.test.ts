import { isProtectedPath } from "../lib/routes";

describe("isProtectedPath (FE-019)", () => {
  test("protects /account and nested account paths", () => {
    expect(isProtectedPath("/account")).toBe(true);
    expect(isProtectedPath("/account/details")).toBe(true);
  });

  test("does not protect public auth pages", () => {
    expect(isProtectedPath("/login")).toBe(false);
    expect(isProtectedPath("/register")).toBe(false);
  });
});
