import assert from "node:assert/strict";
import test from "node:test";
import {
  EMAIL_ERROR,
  LOGIN_PATH,
  PASSWORD_ERROR,
  USERS_PATH,
  authCredentials,
  emailFieldError,
  passwordFieldError,
  withoutSecret,
} from "./credentials.ts";

test("email validation matches the public site rule", () => {
  assert.equal(emailFieldError("name@email.com"), "");
  assert.equal(emailFieldError("  name@email.com  "), "");
  assert.equal(emailFieldError("not-an-email"), EMAIL_ERROR);
  assert.equal(emailFieldError(""), EMAIL_ERROR);
});

test("password is required and is not trimmed", () => {
  assert.equal(passwordFieldError(""), PASSWORD_ERROR);
  assert.equal(passwordFieldError("grill-secret"), "");
  assert.deepEqual(authCredentials(" name@email.com ", " grill "), {
    email: "name@email.com",
    password: " grill ",
  });
  assert.equal(authCredentials("bad", "secret"), null);
});

test("login and registration use the verified paths", () => {
  assert.equal(LOGIN_PATH, "/auth/login");
  assert.equal(USERS_PATH, "/users");
});

test("a failure message never repeats the password", () => {
  assert.equal(
    withoutSecret("Incorrect email or password", "grill-secret"),
    "Incorrect email or password",
  );
  assert.equal(
    withoutSecret("rejected grill-secret", "grill-secret"),
    "That request failed. Check the details and try again.",
  );
});
