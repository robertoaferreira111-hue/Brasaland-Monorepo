import {
  authCredentials,
  EMAIL_ERROR,
  emailFieldError,
  PASSWORD_ERROR,
  passwordFieldError,
  withoutSecret,
} from "./credentials";

describe("emailFieldError", () => {
  test("accepts a trimmed email address", () => {
    expect(emailFieldError("  staff@brasaland.com  ")).toBe("");
  });

  test("rejects a value that is not an email address", () => {
    expect(emailFieldError("not-an-email")).toBe(EMAIL_ERROR);
    expect(emailFieldError("   ")).toBe(EMAIL_ERROR);
  });
});

describe("passwordFieldError", () => {
  test("accepts a non-empty password without trimming it", () => {
    expect(passwordFieldError("secret")).toBe("");
    expect(passwordFieldError(" ")).toBe("");
  });

  test("rejects an empty password", () => {
    expect(passwordFieldError("")).toBe(PASSWORD_ERROR);
  });
});

describe("authCredentials", () => {
  test("returns the trimmed email and the original password", () => {
    expect(authCredentials("  Staff@Brasaland.com  ", " secret ")).toEqual({
      email: "Staff@Brasaland.com",
      password: " secret ",
    });
  });

  test("returns null when the email or the password cannot be used", () => {
    expect(authCredentials("not-an-email", "secret")).toBeNull();
    expect(authCredentials("staff@brasaland.com", "")).toBeNull();
  });
});

describe("withoutSecret", () => {
  test("keeps a message that does not contain the password", () => {
    expect(withoutSecret("Incorrect email or password", "secret-pass")).toBe(
      "Incorrect email or password",
    );
  });

  test("hides a message that repeats the password", () => {
    expect(withoutSecret("rejected secret-pass", "secret-pass")).toBe(
      "That request failed. Check the details and try again.",
    );
    expect(withoutSecret("secret-pass", "")).toBe("secret-pass");
  });
});
