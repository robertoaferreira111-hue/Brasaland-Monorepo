import assert from "node:assert/strict";
import test from "node:test";
import {
  authorizationValue,
  getAccessToken,
  invalidateSession,
  notifySessionExpired,
  resetSessionLifecycleForTests,
  SESSION_EXPIRED_EVENT,
  sessionClearedOnUnauthorized,
  sessionStillActive,
  setTokens,
} from "./token.ts";

class MemoryStorage {
  private readonly values = new Map<string, string>();
  getItem(key: string) {
    return this.values.get(key) ?? null;
  }
  setItem(key: string, value: string) {
    this.values.set(key, value);
  }
  removeItem(key: string) {
    this.values.delete(key);
  }
}

function installBrowser(pathname = "/account") {
  const listeners = new Map();
  Object.defineProperty(globalThis, "window", {
    value: {
      localStorage: new MemoryStorage(),
      location: { pathname },
      addEventListener(type: string, handler: EventListener) {
        const list = listeners.get(type) ?? [];
        list.push(handler);
        listeners.set(type, list);
      },
      removeEventListener() {},
      dispatchEvent(event: Event) {
        for (const handler of listeners.get(event.type) ?? []) {
          handler(event);
        }
        return true;
      },
    },
    configurable: true,
    writable: true,
  });
}

function removeBrowser() {
  Reflect.deleteProperty(globalThis, "window");
  resetSessionLifecycleForTests();
}

test("login stores a token that authenticated requests can attach", () => {
  installBrowser();
  setTokens("live-token", null);
  assert.equal(sessionStillActive(), true);
  assert.equal(authorizationValue(getAccessToken()!), "Bearer live-token");
  removeBrowser();
});

test("logout clears the session so protected views cannot continue", async () => {
  installBrowser("/account");
  resetSessionLifecycleForTests();
  setTokens("access-token", "refresh-token");
  let redirects = 0;
  window.addEventListener(SESSION_EXPIRED_EVENT, () => {
    redirects += 1;
  });
  invalidateSession();
  invalidateSession();
  assert.equal(getAccessToken(), null);
  assert.equal(sessionStillActive(), false);
  assert.equal(redirects, 1);
  await Promise.resolve();
  removeBrowser();
});

test("401 without a successful refresh clears the local session", () => {
  assert.equal(sessionClearedOnUnauthorized(401, false), true);
  assert.equal(sessionClearedOnUnauthorized(401, true), false);
});

test("missing token is treated as an inactive session", () => {
  installBrowser();
  assert.equal(sessionStillActive(), false);
  removeBrowser();
});

test("session expiry does not notify when already on /login", () => {
  installBrowser("/login");
  resetSessionLifecycleForTests();
  let events = 0;
  window.addEventListener(SESSION_EXPIRED_EVENT, () => {
    events += 1;
  });
  notifySessionExpired();
  assert.equal(events, 0);
  removeBrowser();
});
