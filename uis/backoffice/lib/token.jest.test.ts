import {
  authorizationValue,
  clearSession,
  clearTokens,
  getAccessToken,
  getRefreshToken,
  hasAccessToken,
  hasAccessTokenIn,
  invalidateSession,
  notifySessionExpired,
  readAccessToken,
  readRefreshToken,
  readSessionTokens,
  resetSessionLifecycleForTests,
  SESSION_EXPIRED_EVENT,
  sessionClearedOnUnauthorized,
  sessionStillActive,
  setTokens,
  type TokenStore,
  writeSession,
} from "./token";

class MemoryStorage implements TokenStore {
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

function installBrowser(pathname = "/account"): void {
  const listeners = new Map<string, Array<(event: Event) => void>>();
  Object.defineProperty(globalThis, "window", {
    value: {
      localStorage: new MemoryStorage(),
      location: { pathname },
      addEventListener(type: string, handler: (event: Event) => void) {
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

function removeBrowser(): void {
  Reflect.deleteProperty(globalThis, "window");
  resetSessionLifecycleForTests();
}

describe("readAccessToken", () => {
  test("returns the stored access token without surrounding spaces", () => {
    const store = new MemoryStorage();
    store.setItem("brasaland_access_token", "  live-token  ");

    expect(readAccessToken(store)).toBe("live-token");
  });

  test("returns null when the access token is missing or blank", () => {
    const store = new MemoryStorage();

    expect(readAccessToken(store)).toBeNull();
    store.setItem("brasaland_access_token", "   ");
    expect(readAccessToken(store)).toBeNull();
  });
});

describe("readRefreshToken", () => {
  test("returns the stored refresh token without surrounding spaces", () => {
    const store = new MemoryStorage();
    store.setItem("brasaland_refresh_token", "  refresh-token  ");

    expect(readRefreshToken(store)).toBe("refresh-token");
  });

  test("returns null when the refresh token is missing or blank", () => {
    const store = new MemoryStorage();

    expect(readRefreshToken(store)).toBeNull();
    store.setItem("brasaland_refresh_token", " ");
    expect(readRefreshToken(store)).toBeNull();
  });
});

describe("hasAccessTokenIn", () => {
  test("is true when an access token is stored", () => {
    const store = new MemoryStorage();
    store.setItem("brasaland_access_token", "live-token");

    expect(hasAccessTokenIn(store)).toBe(true);
  });

  test("is false when the access token is blank", () => {
    const store = new MemoryStorage();
    store.setItem("brasaland_access_token", " ");

    expect(hasAccessTokenIn(store)).toBe(false);
  });
});

describe("writeSession", () => {
  test("stores a trimmed access token and refresh token", () => {
    const store = new MemoryStorage();

    writeSession(store, "  access  ", "  refresh  ");

    expect(readAccessToken(store)).toBe("access");
    expect(readRefreshToken(store)).toBe("refresh");
  });

  test("does not store a blank access token and drops a blank refresh token", () => {
    const store = new MemoryStorage();
    store.setItem("brasaland_refresh_token", "old-refresh");

    writeSession(store, "   ", "refresh");
    expect(readAccessToken(store)).toBeNull();
    expect(readRefreshToken(store)).toBe("old-refresh");

    writeSession(store, "access", "  ");
    expect(readAccessToken(store)).toBe("access");
    expect(readRefreshToken(store)).toBeNull();
  });
});

describe("clearSession", () => {
  test("removes the access token and the refresh token", () => {
    const store = new MemoryStorage();
    writeSession(store, "access", "refresh");

    clearSession(store);

    expect(readAccessToken(store)).toBeNull();
    expect(readRefreshToken(store)).toBeNull();
  });

  test("leaves an already empty store empty", () => {
    const store = new MemoryStorage();

    clearSession(store);

    expect(readAccessToken(store)).toBeNull();
    expect(readRefreshToken(store)).toBeNull();
  });
});

describe("authorizationValue", () => {
  test("builds a bearer credential from the access token", () => {
    expect(authorizationValue("live-token")).toBe("Bearer live-token");
  });

  test("does not turn an empty token into a usable credential", () => {
    expect(authorizationValue("")).toBe("Bearer ");
    expect(authorizationValue("").trim()).not.toBe("Bearer live-token");
  });
});

describe("getAccessToken", () => {
  afterEach(removeBrowser);

  test("reads the access token from the browser store", () => {
    installBrowser();
    setTokens("live-token", null);

    expect(getAccessToken()).toBe("live-token");
  });

  test("returns null when there is no browser", () => {
    removeBrowser();

    expect(getAccessToken()).toBeNull();
  });
});

describe("getRefreshToken", () => {
  afterEach(removeBrowser);

  test("reads the refresh token from the browser store", () => {
    installBrowser();
    setTokens("access", "refresh-token");

    expect(getRefreshToken()).toBe("refresh-token");
  });

  test("returns null when there is no browser", () => {
    removeBrowser();

    expect(getRefreshToken()).toBeNull();
  });
});

describe("hasAccessToken", () => {
  afterEach(removeBrowser);

  test("is true when the browser holds an access token", () => {
    installBrowser();
    setTokens("live-token", null);

    expect(hasAccessToken()).toBe(true);
  });

  test("is false when there is no browser", () => {
    removeBrowser();

    expect(hasAccessToken()).toBe(false);
  });
});

describe("setTokens", () => {
  afterEach(removeBrowser);

  test("saves the session in the browser", () => {
    installBrowser();

    setTokens("  access  ", "refresh");

    expect(getAccessToken()).toBe("access");
    expect(getRefreshToken()).toBe("refresh");
  });

  test("does nothing when there is no browser", () => {
    removeBrowser();

    expect(() => setTokens("access", "refresh")).not.toThrow();
    expect(getAccessToken()).toBeNull();
  });
});

describe("clearTokens", () => {
  afterEach(removeBrowser);

  test("removes the browser session", () => {
    installBrowser();
    setTokens("access", "refresh");

    clearTokens();

    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });

  test("does nothing when there is no browser", () => {
    removeBrowser();

    expect(() => clearTokens()).not.toThrow();
    expect(sessionStillActive()).toBe(false);
  });
});

describe("readSessionTokens", () => {
  test("accepts the access and refresh fields the API returns", () => {
    expect(
      readSessionTokens({
        access_token: "  access  ",
        refresh_token: " refresh ",
      }),
    ).toEqual({ access: "access", refresh: "refresh" });
  });

  test("rejects a body that does not contain an access token", () => {
    expect(readSessionTokens(null)).toBeNull();
    expect(readSessionTokens(["access"])).toBeNull();
    expect(readSessionTokens({ refresh_token: "refresh" })).toBeNull();
    expect(readSessionTokens({ access_token: "   " })).toBeNull();
  });
});

describe("sessionClearedOnUnauthorized", () => {
  test("clears the session on a 401 that was not refreshed", () => {
    expect(sessionClearedOnUnauthorized(401, false)).toBe(true);
  });

  test("keeps the session when refresh already replaced it or the status is not 401", () => {
    expect(sessionClearedOnUnauthorized(401, true)).toBe(false);
    expect(sessionClearedOnUnauthorized(500, false)).toBe(false);
  });
});

describe("notifySessionExpired", () => {
  afterEach(removeBrowser);

  test("asks the app to open login when a session expires away from the login page", () => {
    installBrowser("/account");
    let notices = 0;
    window.addEventListener(SESSION_EXPIRED_EVENT, () => {
      notices += 1;
    });

    notifySessionExpired();

    expect(notices).toBe(1);
  });

  test("does not notify when already on login or when there is no browser", () => {
    installBrowser("/login");
    let notices = 0;
    window.addEventListener(SESSION_EXPIRED_EVENT, () => {
      notices += 1;
    });
    notifySessionExpired();
    expect(notices).toBe(0);

    removeBrowser();
    expect(() => notifySessionExpired()).not.toThrow();
  });
});

describe("invalidateSession", () => {
  afterEach(removeBrowser);

  test("clears the stored tokens and notifies once", async () => {
    installBrowser("/account");
    resetSessionLifecycleForTests();
    setTokens("access", "refresh");
    let notices = 0;
    window.addEventListener(SESSION_EXPIRED_EVENT, () => {
      notices += 1;
    });

    invalidateSession();
    invalidateSession();

    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
    expect(notices).toBe(1);
    await Promise.resolve();
  });

  test("does not throw when there is no browser session to clear", () => {
    removeBrowser();

    expect(() => invalidateSession()).not.toThrow();
    expect(sessionStillActive()).toBe(false);
  });
});

describe("sessionStillActive", () => {
  afterEach(removeBrowser);

  test("is true only while an access token is stored", () => {
    installBrowser();
    setTokens("live-token", null);

    expect(sessionStillActive()).toBe(true);
  });

  test("is false when the access token is missing", () => {
    installBrowser();

    expect(sessionStillActive()).toBe(false);
  });
});

describe("resetSessionLifecycleForTests", () => {
  afterEach(removeBrowser);

  test("allows a later expiry to notify again", async () => {
    installBrowser("/account");
    resetSessionLifecycleForTests();
    setTokens("access", null);
    let notices = 0;
    window.addEventListener(SESSION_EXPIRED_EVENT, () => {
      notices += 1;
    });

    invalidateSession();
    await Promise.resolve();
    resetSessionLifecycleForTests();
    setTokens("access-again", null);
    invalidateSession();

    expect(notices).toBe(2);
  });

  test("does not itself create a session", () => {
    removeBrowser();

    resetSessionLifecycleForTests();

    expect(sessionStillActive()).toBe(false);
  });
});
