import { describe, expect, it, vi } from "vitest";

import {
  FORGOT_CONFIRMATION_MESSAGE,
  TOKEN_STORAGE_KEY,
  buildChangePasswordPayload,
  buildForgotPasswordPayload,
  buildResetPasswordPayload,
  changePasswordRequest,
  createAuthHeaders,
  forgotPasswordRequest,
  getResetTokenFromSearch,
  isValidEmail,
  loginRequest,
  resetPasswordRequest,
  resolveApiBase,
  shouldBlockDuplicateSubmit,
  validatePasswordLength,
  validatePasswordMatch,
} from "../js/auth-api.js";

describe("resolveApiBase", () => {
  it("uses local API by default", () => {
    expect(resolveApiBase({ hostname: "127.0.0.1", protocol: "http:", search: "" })).toBe(
      "http://127.0.0.1:8000",
    );
  });

  it("honors ?api= override", () => {
    expect(
      resolveApiBase({
        hostname: "127.0.0.1",
        protocol: "http:",
        search: "?api=https://example.com/api/",
      }),
    ).toBe("https://example.com/api");
  });
});

describe("validation helpers", () => {
  it("validates email format", () => {
    expect(isValidEmail("lucia@brasaland.com")).toBe(true);
    expect(isValidEmail("bad")).toBe(false);
  });

  it("validates password length and match without echoing secrets", () => {
    expect(validatePasswordLength("short")).toMatch(/at least 8/i);
    expect(validatePasswordLength("longenough")).toBe("");
    expect(validatePasswordMatch("abc12345", "abc12345")).toBe("");
    expect(validatePasswordMatch("abc12345", "other")).toMatch(/must match/i);
    expect(validatePasswordMatch("secret-value", "other")).not.toContain("secret-value");
  });

  it("blocks duplicate submits while in flight", () => {
    expect(shouldBlockDuplicateSubmit(true)).toBe(true);
    expect(shouldBlockDuplicateSubmit(false)).toBe(false);
  });
});

describe("payload builders", () => {
  it("builds forgot-password payload", () => {
    expect(buildForgotPasswordPayload("  Lucia@Brasaland.com ")).toEqual({
      email: "lucia@brasaland.com",
    });
  });

  it("builds reset-password payload with token", () => {
    expect(buildResetPasswordPayload("tok_abc", "NewPass456!")).toEqual({
      token: "tok_abc",
      new_password: "NewPass456!",
    });
  });

  it("builds change-password payload", () => {
    expect(buildChangePasswordPayload("old", "newpass12")).toEqual({
      current_password: "old",
      new_password: "newpass12",
    });
  });

  it("reads reset token from query string", () => {
    expect(getResetTokenFromSearch("?token=abc%2F123&x=1")).toBe("abc/123");
    expect(getResetTokenFromSearch("")).toBe("");
  });
});

describe("API requests", () => {
  it("posts forgot-password and returns confirmation", async () => {
    const fetchImpl = vi.fn(async (url, init) => {
      expect(url).toBe("http://127.0.0.1:8000/auth/forgot-password");
      expect(JSON.parse(init.body)).toEqual({ email: "lucia@brasaland.com" });
      return {
        ok: true,
        json: async () => ({ message: FORGOT_CONFIRMATION_MESSAGE }),
      };
    });

    const result = await forgotPasswordRequest(
      "http://127.0.0.1:8000",
      "lucia@brasaland.com",
      { fetchImpl },
    );
    expect(result.message).toBe(FORGOT_CONFIRMATION_MESSAGE);
    expect(fetchImpl).toHaveBeenCalledOnce();
  });

  it("surfaces backend errors for forgot-password", async () => {
    const fetchImpl = vi.fn(async () => ({
      ok: false,
      status: 503,
      json: async () => ({
        detail: "Unable to send recovery email. Please try again later.",
      }),
    }));

    await expect(
      forgotPasswordRequest("http://127.0.0.1:8000", "lucia@brasaland.com", {
        fetchImpl,
      }),
    ).rejects.toThrow(/Unable to send recovery email/i);
  });

  it("posts reset-password payload", async () => {
    const fetchImpl = vi.fn(async (url, init) => {
      expect(url).toBe("http://127.0.0.1:8000/auth/reset-password");
      expect(JSON.parse(init.body)).toEqual({
        token: "raw-token",
        new_password: "NewPass456!",
      });
      return {
        ok: true,
        json: async () => ({ message: "Password has been reset successfully." }),
      };
    });

    const body = await resetPasswordRequest(
      "http://127.0.0.1:8000",
      "raw-token",
      "NewPass456!",
      { fetchImpl },
    );
    expect(body.message).toMatch(/reset successfully/i);
  });

  it("rejects invalid reset tokens from the API", async () => {
    const fetchImpl = vi.fn(async () => ({
      ok: false,
      status: 400,
      json: async () => ({ detail: "Invalid or expired reset token" }),
    }));

    await expect(
      resetPasswordRequest("http://127.0.0.1:8000", "bad", "NewPass456!", {
        fetchImpl,
      }),
    ).rejects.toThrow(/Invalid or expired reset token/i);
  });

  it("sends Bearer token on change-password", async () => {
    const fetchImpl = vi.fn(async (_url, init) => {
      expect(init.headers.Authorization).toBe("Bearer access-123");
      expect(JSON.parse(init.body)).toEqual({
        current_password: "ChangeMe123!",
        new_password: "NewPass456!",
      });
      return {
        ok: true,
        json: async () => ({ message: "Password has been changed successfully." }),
      };
    });

    await changePasswordRequest(
      "http://127.0.0.1:8000",
      "ChangeMe123!",
      "NewPass456!",
      { fetchImpl, accessToken: "access-123" },
    );
    expect(createAuthHeaders("access-123").Authorization).toBe("Bearer access-123");
  });

  it("stores login access token via loginRequest body", async () => {
    const fetchImpl = vi.fn(async (_url, init) => {
      expect(JSON.parse(init.body)).toEqual({
        email: "lucia@brasaland.com",
        password: "ChangeMe123!",
      });
      return {
        ok: true,
        json: async () => ({
          access_token: "jwt-token",
          token_type: "bearer",
          email: "lucia@brasaland.com",
        }),
      };
    });

    const result = await loginRequest(
      "http://127.0.0.1:8000",
      "lucia@brasaland.com",
      "ChangeMe123!",
      { fetchImpl },
    );
    expect(result.access_token).toBe("jwt-token");
    expect(TOKEN_STORAGE_KEY).toBe("brasaland_access_token");
  });
});
