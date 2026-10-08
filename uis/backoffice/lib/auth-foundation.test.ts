import assert from "node:assert/strict";
import test from "node:test";
import { publicErrorText } from "./errors.ts";
import {
  authorizationValue,
  clearSession,
  clearTokens,
  getAccessToken,
  hasAccessToken,
  hasAccessTokenIn,
  readAccessToken,
  readRefreshToken,
  readSessionTokens,
  sessionClearedOnUnauthorized,
  setTokens,
  writeSession,
  type TokenStore,
} from "./token.ts";

class MemoryStore implements TokenStore {
  private readonly values = new Map<string, string>();

  getItem(key: string): string | null {
    return this.values.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    this.values.set(key, value);
  }

  removeItem(key: string): void {
    this.values.delete(key);
  }
}

test("browser helpers do not touch storage when window is absent", () => {
  assert.equal(typeof globalThis.window, "undefined");
  assert.equal(getAccessToken(), null);
  assert.equal(hasAccessToken(), false);
  setTokens("access-token", "refresh-token");
  clearTokens();
  assert.equal(getAccessToken(), null);
});

test("session store writes, reads, and clears the access token", () => {
  const store = new MemoryStore();
  assert.equal(hasAccessTokenIn(store), false);
  writeSession(store, " access-token ", " refresh-token ");
  assert.equal(readAccessToken(store), "access-token");
  assert.equal(readRefreshToken(store), "refresh-token");
  assert.equal(hasAccessTokenIn(store), true);
  assert.equal(authorizationValue("access-token"), "Bearer access-token");
  clearSession(store);
  assert.equal(readAccessToken(store), null);
  assert.equal(readRefreshToken(store), null);
  assert.equal(hasAccessTokenIn(store), false);
});

test("blank tokens are not stored", () => {
  const store = new MemoryStore();
  writeSession(store, "   ", "refresh-token");
  assert.equal(hasAccessTokenIn(store), false);
  writeSession(store, "access-token", "   ");
  assert.equal(readAccessToken(store), "access-token");
  assert.equal(readRefreshToken(store), null);
});

test("login payloads accept the token field names the client understands", () => {
  assert.deepEqual(readSessionTokens({ access_token: "a", refresh_token: "r" }), {
    access: "a",
    refresh: "r",
  });
  assert.deepEqual(readSessionTokens({ token: " plain " }), {
    access: "plain",
    refresh: null,
  });
  assert.deepEqual(readSessionTokens({ accessToken: "camel", refreshToken: "r2" }), {
    access: "camel",
    refresh: "r2",
  });
  assert.equal(readSessionTokens({}), null);
  assert.equal(readSessionTokens({ access_token: "  " }), null);
});

test("a protected 401 clears the session unless refresh already replaced it", () => {
  assert.equal(sessionClearedOnUnauthorized(401, false), true);
  assert.equal(sessionClearedOnUnauthorized(401, true), false);
  assert.equal(sessionClearedOnUnauthorized(200, false), false);
});

test("API errors stay free of raw bodies and token-shaped text", () => {
  assert.equal(
    publicErrorText(401, JSON.stringify({ detail: "Incorrect email or password" })),
    "Incorrect email or password",
  );
  const jwt = "aaaa.bbbb.cccc";
  assert.equal(publicErrorText(500, jwt), "Request failed (500)");
  assert.equal(
    publicErrorText(500, JSON.stringify({ message: `Bearer ${jwt}` })),
    "Request failed (500)",
  );
  assert.equal(publicErrorText(400, "not json and not a known field"), "Request failed (400)");
});
