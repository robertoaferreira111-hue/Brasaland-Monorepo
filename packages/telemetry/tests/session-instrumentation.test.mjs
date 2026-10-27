import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const here = dirname(fileURLToPath(import.meta.url));
const backoffice = resolve(here, "../../../uis/backoffice");

function memoryStorage(seed = {}) {
  const data = new Map(Object.entries(seed));
  return {
    getItem(key) {
      return data.has(key) ? data.get(key) : null;
    },
    setItem(key, value) {
      data.set(key, String(value));
    },
    removeItem(key) {
      data.delete(key);
    },
  };
}

function loadSession({ fetchImpl, telemetry, storage }) {
  const location = {
    hostname: "localhost",
    protocol: "http:",
    search: "",
    pathname: "/account/",
    replaced: "",
    replace(url) {
      location.replaced = url;
    },
  };
  const sandbox = {
    localStorage: storage,
    performance: { now: () => 40 },
    fetch: fetchImpl,
    URLSearchParams,
    Headers,
    location,
    console,
  };
  sandbox.window = sandbox;
  sandbox.BrasalandTelemetry = telemetry;
  vm.runInNewContext(readFileSync(resolve(backoffice, "js/session.js"), "utf8"), sandbox);
  return sandbox;
}

test("apiFetch records one API event and still returns the response", async () => {
  const notes = [];
  const sandbox = loadSession({
    storage: memoryStorage(),
    telemetry: { noteApi(input) { notes.push(input); } },
    fetchImpl: async () => ({ ok: true, status: 200, json: async () => ({ items: [] }) }),
  });
  const response = await sandbox.BrasalandSession.apiFetch("/suppliers", { auth: false });
  assert.equal(response.status, 200);
  assert.equal(notes.length, 1);
  assert.deepEqual(
    { method: notes[0].method, path: notes[0].path, status: notes[0].status, durationMs: notes[0].durationMs },
    { method: "GET", path: "/suppliers", status: 200, durationMs: 0 },
  );
});

test("apiFetch records a network failure and still throws", async () => {
  const notes = [];
  const sandbox = loadSession({
    storage: memoryStorage(),
    telemetry: { noteApi(input) { notes.push(input); } },
    fetchImpl: async () => {
      throw new Error("offline");
    },
  });
  await assert.rejects(() => sandbox.BrasalandSession.apiFetch("/suppliers", { auth: false }), /offline/);
  assert.equal(notes.length, 1);
  assert.equal(notes[0].status, 0);
  assert.equal(notes[0].path, "/suppliers");
});

test("a throwing telemetry client does not block apiFetch or logout", async () => {
  const storage = memoryStorage({ "brasaland.access_token": "token-value" });
  const sandbox = loadSession({
    storage,
    telemetry: {
      noteApi() {
        throw new Error("telemetry down");
      },
      noteLogout() {
        throw new Error("telemetry down");
      },
    },
    fetchImpl: async () => ({ ok: true, status: 204 }),
  });
  const response = await sandbox.BrasalandSession.apiFetch("/suppliers", { auth: false });
  assert.equal(response.status, 204);
  await sandbox.BrasalandSession.logout();
  assert.equal(storage.getItem("brasaland.access_token"), null);
  assert.equal(sandbox.location.replaced, "/login/?next=%2Faccount%2F");
});

test("logout records the business event before the token is cleared", async () => {
  const order = [];
  const storage = memoryStorage({ "brasaland.access_token": "token-value" });
  const sandbox = loadSession({
    storage,
    telemetry: {
      noteLogout() {
        order.push(storage.getItem("brasaland.access_token") ? "token-present" : "token-gone");
      },
      noteApi(input) {
        order.push(input.path);
        assert.equal(JSON.stringify(input).includes("token-value"), false);
      },
    },
    fetchImpl: async (_url, options) => {
      assert.equal(options.method, "POST");
      return { ok: true, status: 204 };
    },
  });
  await sandbox.BrasalandSession.logout();
  assert.deepEqual(order, ["token-present", "/auth/logout"]);
  assert.equal(storage.getItem("brasaland.access_token"), null);
});

test("page scripts call the current-page hook only on approved screens", () => {
  const login = readFileSync(resolve(backoffice, "js/login-page.js"), "utf8");
  const register = readFileSync(resolve(backoffice, "js/register-page.js"), "utf8");
  const account = readFileSync(resolve(backoffice, "js/account-page.js"), "utf8");
  const directory = readFileSync(resolve(backoffice, "app.js"), "utf8");
  assert.match(login, /noteLoginFailure\(response\.status\)/);
  assert.match(login, /saveTokens\([\s\S]*?noteLoginSuccess\(\)/);
  assert.match(login, /noteCurrentPage\(\)/);
  assert.match(register, /noteLoginFailure\(login\.status\)/);
  assert.equal(register.includes("noteCurrentPage"), false);
  assert.match(account, /requireSession\(\)[\s\S]*noteCurrentPage\(\)/);
  assert.match(directory, /requireSession\(\)[\s\S]*noteCurrentPage\(\)/);
  assert.match(readFileSync(resolve(backoffice, "login/index.html"), "utf8"), /data-telemetry-page="login"/);
  assert.match(readFileSync(resolve(backoffice, "index.html"), "utf8"), /data-telemetry-page="suppliers"/);
  assert.match(readFileSync(resolve(backoffice, "account/index.html"), "utf8"), /data-telemetry-page="account"/);
  assert.equal(readFileSync(resolve(backoffice, "register/index.html"), "utf8").includes("data-telemetry-page"), false);
});
