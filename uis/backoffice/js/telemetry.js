/* Generated from packages/telemetry/src/backoffice.ts. */
"use strict";
(() => {
  // packages/telemetry/src/capture.ts
  var OPS_PAGES = /* @__PURE__ */ new Set([
    "login",
    "inbound_orders",
    "outbound_orders",
    "stock",
    "products",
    "suppliers",
    "account"
  ]);
  var METHODS = /* @__PURE__ */ new Set(["GET", "POST", "PUT", "PATCH", "DELETE"]);
  var ATTEMPTS_KEY = "brasaland.telemetry.login_attempts";
  function isOpsPage(value) {
    return OPS_PAGES.has(value);
  }
  function routeTemplate(path) {
    const withoutQuery = path.split("?")[0] ?? "";
    let pathname = withoutQuery;
    if (withoutQuery.startsWith("http://") || withoutQuery.startsWith("https://")) {
      try {
        pathname = new URL(withoutQuery).pathname;
      } catch {
        pathname = withoutQuery;
      }
    }
    if (!pathname.startsWith("/")) {
      pathname = `/${pathname}`;
    }
    const trimmed = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
    return trimmed.replace(/\/suppliers\/[^/]+/g, "/suppliers/{id}");
  }
  function attemptBucket(attempts) {
    if (attempts <= 1) {
      return "1";
    }
    if (attempts <= 5) {
      return "2-5";
    }
    return "6+";
  }
  function loginFailureProperties(status, attempts) {
    let errorCode = null;
    if (status === 401) {
      errorCode = "invalid_credentials";
    } else if (status === 423) {
      errorCode = "account_locked";
    } else if (status === 400 || status === 422) {
      errorCode = "validation_error";
    }
    if (!errorCode) {
      return null;
    }
    const count = Number.isFinite(attempts) && attempts > 0 ? Math.floor(attempts) : 1;
    return { error_code: errorCode, attempt_bucket: attemptBucket(count) };
  }
  function apiErrorCode(status) {
    if (status === 0) {
      return "network_error";
    }
    if (status === 401) {
      return "unauthorized";
    }
    if (status === 403) {
      return "forbidden";
    }
    if (status === 404) {
      return "not_found";
    }
    if (status === 408) {
      return "timeout";
    }
    if (status === 409) {
      return "conflict";
    }
    if (status === 400 || status === 422) {
      return "validation_error";
    }
    if (status >= 500 && status <= 599) {
      return "internal_error";
    }
    return null;
  }
  function apiObservation(input) {
    const method2 = input.method.toUpperCase();
    if (!METHODS.has(method2)) {
      return null;
    }
    const routeTemplateValue = routeTemplate(input.path);
    if (!routeTemplateValue || routeTemplateValue.includes("/telemetry/events")) {
      return null;
    }
    const durationMs2 = Number.isFinite(input.durationMs) && input.durationMs >= 0 ? input.durationMs : 0;
    const httpMethod = method2;
    if (input.status >= 200 && input.status <= 299) {
      return {
        eventType: "api_request_completed",
        properties: {
          route_template: routeTemplateValue,
          method: httpMethod,
          status_code: input.status,
          duration_ms: durationMs2
        }
      };
    }
    const errorCode = apiErrorCode(input.status);
    if (!errorCode || input.status < 0 || input.status > 599) {
      return null;
    }
    return {
      eventType: "api_request_failed",
      properties: {
        route_template: routeTemplateValue,
        method: httpMethod,
        status_code: input.status,
        error_code: errorCode,
        duration_ms: durationMs2
      }
    };
  }
  function pageLoadProperties(page2, durationMs2, connection) {
    const duration_ms = Number.isFinite(durationMs2) && durationMs2 >= 0 ? durationMs2 : 0;
    if (connection === "wifi" || connection === "cellular" || connection === "ethernet" || connection === "unknown") {
      return { page: page2, duration_ms, connection_type: connection };
    }
    return { page: page2, duration_ms };
  }
  function observeCurrentPage(hooks, env) {
    if (!env.page) {
      return;
    }
    if (env.includeView !== false) {
      hooks.notePage(env.page);
    }
    if (env.includeLoad !== false) {
      hooks.notePageLoad(env.page, env.durationMs, env.connection);
    }
  }
  function createCaptureHooks(track2, storage2) {
    function readAttempts() {
      const raw = storage2?.getItem(ATTEMPTS_KEY);
      const value = Number(raw);
      return Number.isFinite(value) && value > 0 ? Math.floor(value) : 0;
    }
    function writeAttempts(value) {
      try {
        storage2?.setItem(ATTEMPTS_KEY, String(value));
      } catch {
      }
    }
    return {
      noteLoginSuccess() {
        writeAttempts(0);
        track2("user_logged_in", { auth_method: "password" });
      },
      noteLoginFailure(status) {
        const next = readAttempts() + 1;
        writeAttempts(next);
        const properties = loginFailureProperties(status, next);
        if (!properties) {
          return;
        }
        track2("user_login_failed", properties);
      },
      noteLogout() {
        track2("user_logged_out", { reason: "user_action" });
      },
      noteApi(input) {
        const event = apiObservation(input);
        if (!event) {
          return;
        }
        track2(event.eventType, event.properties);
      },
      notePage(page2) {
        if (!isOpsPage(page2)) {
          return;
        }
        track2("page_viewed", { page: page2 });
      },
      notePageLoad(page2, durationMs2, connection) {
        if (!isOpsPage(page2)) {
          return;
        }
        track2("page_load_completed", pageLoadProperties(page2, durationMs2, connection));
      }
    };
  }

  // packages/telemetry/src/contract.ts
  var SCHEMA_VERSION = "1.0.0";
  var TELEMETRY_EVENTS = [
    "inbound_order_created",
    "outbound_order_created",
    "stock_waste_registered",
    "stock_threshold_triggered",
    "direct_stock_edit_rejected",
    "ingredient_price_variance_detected",
    "product_validation_failed",
    "user_logged_in",
    "user_login_failed",
    "user_logged_out",
    "page_viewed",
    "workflow_abandoned",
    "api_request_completed",
    "api_request_failed",
    "page_load_completed"
  ];
  var country = { kind: "country", values: ["CO", "US"] };
  var currency = { kind: "currency", values: ["COP", "USD"] };
  var category = {
    kind: "string",
    values: ["protein", "vegetable", "sauce", "beverage", "packaging", "cleaning"]
  };
  var unit = { kind: "string", values: ["kg", "unit", "liter"] };
  var id = { kind: "string" };
  var positive = { kind: "number", exclusiveMin: 0 };
  var nonNegative = { kind: "number", min: 0 };
  var anyNumber = { kind: "number" };
  var page = {
    kind: "string",
    values: [
      "login",
      "inbound_orders",
      "outbound_orders",
      "stock",
      "products",
      "suppliers",
      "account"
    ]
  };
  var method = {
    kind: "string",
    values: ["GET", "POST", "PUT", "PATCH", "DELETE"]
  };
  var inventoryFields = {
    location_id: id,
    country,
    product_id: id,
    product_category: category,
    quantity: positive,
    unit,
    currency
  };
  var inventoryRequired = [
    "location_id",
    "country",
    "product_id",
    "product_category",
    "quantity",
    "unit",
    "currency"
  ];
  function inventory(extraRequired, extraFields, quantity = positive) {
    return {
      required: [...inventoryRequired, ...extraRequired],
      optional: [],
      currencyPair: true,
      fields: { ...inventoryFields, quantity, ...extraFields }
    };
  }
  var RULES = {
    inbound_order_created: inventory(
      ["supplier_id", "unit_cost", "inbound_order_id"],
      { supplier_id: id, unit_cost: positive, inbound_order_id: id }
    ),
    outbound_order_created: inventory(
      ["outbound_order_id", "reason"],
      { outbound_order_id: id, reason: { kind: "string", values: ["prep_consumption"] } }
    ),
    stock_waste_registered: inventory(
      ["outbound_order_id", "reason"],
      {
        outbound_order_id: id,
        reason: { kind: "string", values: ["expired", "kitchen_error", "theft_suspected"] }
      }
    ),
    stock_threshold_triggered: inventory(
      ["minimum_quantity"],
      { minimum_quantity: positive },
      nonNegative
    ),
    direct_stock_edit_rejected: inventory(
      ["rejection_code"],
      { rejection_code: { kind: "string", values: ["direct_edit_forbidden"] } },
      anyNumber
    ),
    ingredient_price_variance_detected: inventory(
      [
        "supplier_id",
        "unit_cost",
        "historical_unit_cost",
        "variance_pct",
        "variance_threshold_pct",
        "inbound_order_id"
      ],
      {
        supplier_id: id,
        unit_cost: positive,
        historical_unit_cost: positive,
        variance_pct: anyNumber,
        variance_threshold_pct: positive,
        inbound_order_id: id
      }
    ),
    product_validation_failed: {
      required: ["error_code", "field", "entity"],
      optional: ["product_id", "location_id", "country"],
      fields: {
        error_code: {
          kind: "string",
          values: [
            "missing_required_field",
            "invalid_unit",
            "invalid_category",
            "invalid_quantity",
            "invalid_currency",
            "invalid_country"
          ]
        },
        field: {
          kind: "string",
          values: [
            "product_id",
            "product_category",
            "quantity",
            "unit",
            "currency",
            "country",
            "location_id",
            "supplier_id",
            "reason"
          ]
        },
        entity: { kind: "string", values: ["product", "inbound_order", "outbound_order"] },
        product_id: id,
        location_id: id,
        country
      }
    },
    user_logged_in: {
      required: ["auth_method"],
      optional: [],
      fields: { auth_method: { kind: "string", values: ["password"] } }
    },
    user_login_failed: {
      required: ["error_code", "attempt_bucket"],
      optional: [],
      fields: {
        error_code: {
          kind: "string",
          values: ["invalid_credentials", "validation_error", "account_locked"]
        },
        attempt_bucket: { kind: "string", values: ["1", "2-5", "6+"] }
      }
    },
    user_logged_out: {
      required: ["reason"],
      optional: [],
      fields: {
        reason: { kind: "string", values: ["user_action", "token_revoked", "session_expired"] }
      }
    },
    page_viewed: {
      required: ["page"],
      optional: ["referrer_page"],
      fields: { page, referrer_page: page }
    },
    workflow_abandoned: {
      required: ["workflow", "step_reached", "duration_ms"],
      optional: ["location_id", "country"],
      fields: {
        workflow: {
          kind: "string",
          values: ["inbound_order_create", "outbound_order_create", "waste_register"]
        },
        step_reached: {
          kind: "string",
          values: ["form_opened", "product_selected", "quantity_entered", "review", "submit_attempted"]
        },
        duration_ms: nonNegative,
        location_id: id,
        country
      }
    },
    api_request_completed: {
      required: ["route_template", "method", "status_code", "duration_ms"],
      optional: [],
      fields: {
        route_template: id,
        method,
        status_code: { kind: "integer", min: 200, max: 299 },
        duration_ms: nonNegative
      }
    },
    api_request_failed: {
      required: ["route_template", "method", "status_code", "error_code", "duration_ms"],
      optional: [],
      fields: {
        route_template: id,
        method,
        status_code: { kind: "integer", min: 0, max: 599 },
        error_code: {
          kind: "string",
          values: [
            "unauthorized",
            "forbidden",
            "not_found",
            "validation_error",
            "conflict",
            "internal_error",
            "timeout",
            "network_error"
          ]
        },
        duration_ms: nonNegative
      }
    },
    page_load_completed: {
      required: ["page", "duration_ms"],
      optional: ["connection_type"],
      fields: {
        page,
        duration_ms: nonNegative,
        connection_type: { kind: "string", values: ["wifi", "cellular", "ethernet", "unknown"] }
      }
    }
  };
  function isTelemetryEventName(value) {
    return TELEMETRY_EVENTS.includes(value);
  }
  function fieldOk(value, rule, allowNull) {
    if (value === null) {
      return allowNull;
    }
    if (rule.kind === "string" || rule.kind === "country" || rule.kind === "currency") {
      if (typeof value !== "string" || value.trim() === "") {
        return false;
      }
      return rule.values === void 0 || rule.values.includes(value);
    }
    if (typeof value !== "number" || !Number.isFinite(value)) {
      return false;
    }
    if (rule.kind === "integer" && !Number.isInteger(value)) {
      return false;
    }
    if (rule.min !== void 0 && value < rule.min) {
      return false;
    }
    if (rule.max !== void 0 && value > rule.max) {
      return false;
    }
    if (rule.exclusiveMin !== void 0 && !(value > rule.exclusiveMin)) {
      return false;
    }
    return true;
  }
  function allowlistedProperties(eventType, properties) {
    if (!isTelemetryEventName(eventType)) {
      return null;
    }
    const rule = RULES[eventType];
    const record = properties;
    const allowed = /* @__PURE__ */ new Set([...rule.required, ...rule.optional]);
    for (const key of Object.keys(record)) {
      if (!allowed.has(key)) {
        return null;
      }
    }
    for (const key of rule.required) {
      if (!Object.prototype.hasOwnProperty.call(record, key)) {
        return null;
      }
      const field = rule.fields[key];
      if (!field || !fieldOk(record[key], field, false)) {
        return null;
      }
    }
    for (const key of rule.optional) {
      if (!Object.prototype.hasOwnProperty.call(record, key)) {
        continue;
      }
      const field = rule.fields[key];
      const allowNull = key === "referrer_page";
      if (!field || !fieldOk(record[key], field, allowNull)) {
        return null;
      }
    }
    if (rule.currencyPair && !currencyMatchesCountry(record)) {
      return null;
    }
    const copy = {};
    for (const key of [...rule.required, ...rule.optional]) {
      if (Object.prototype.hasOwnProperty.call(record, key)) {
        copy[key] = record[key];
      }
    }
    return copy;
  }
  function currencyMatchesCountry(record) {
    if (record.country === "CO") {
      return record.currency === "COP";
    }
    if (record.country === "US") {
      return record.currency === "USD";
    }
    return false;
  }

  // packages/telemetry/src/envelope.ts
  var UUID_PATTERN = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$/;
  function resolveUserId(eventType, userId) {
    if (eventType === "user_login_failed") {
      return null;
    }
    if (typeof userId !== "string") {
      return null;
    }
    const trimmed = userId.trim();
    if (!trimmed || trimmed.includes("@")) {
      return null;
    }
    return trimmed;
  }
  function buildTelemetryEvent(input) {
    const properties = allowlistedProperties(input.eventType, input.properties);
    if (!properties) {
      return null;
    }
    const eventId = input.newId();
    const requestId = input.newId();
    const sessionId = input.sessionId;
    if (!UUID_PATTERN.test(eventId) || !UUID_PATTERN.test(requestId) || !UUID_PATTERN.test(sessionId)) {
      return null;
    }
    const timestamp = new Date(input.nowMs).toISOString();
    if (!timestamp.endsWith("Z")) {
      return null;
    }
    return {
      eventId,
      timestamp,
      sessionId,
      userId: resolveUserId(input.eventType, input.userId),
      event_type: input.eventType,
      entity_action: input.eventType,
      schemaVersion: SCHEMA_VERSION,
      requestId,
      properties
    };
  }

  // packages/telemetry/src/service.ts
  var FLUSH_INTERVAL_MS = 1e4;
  var BATCH_SIZE = 20;
  var MAX_RETRIES = 3;
  var BACKOFF_BASE_MS = 1e3;
  var MAX_BEACON_BYTES = 6e4;
  function createTelemetryService(deps) {
    const flushIntervalMs = deps.flushIntervalMs ?? FLUSH_INTERVAL_MS;
    const batchSize = deps.batchSize ?? BATCH_SIZE;
    const maxRetries = deps.maxRetries ?? MAX_RETRIES;
    const backoffBaseMs = deps.backoffBaseMs ?? BACKOFF_BASE_MS;
    const maxBeaconBytes = deps.maxBeaconBytes ?? MAX_BEACON_BYTES;
    let queue = [];
    let timer = null;
    let delayTimer = null;
    let releaseDelay = null;
    let inFlight = null;
    let inFlightIds = /* @__PURE__ */ new Set();
    let flushAgain = false;
    let stopped = false;
    const stats = {
      droppedAfterRetry: 0,
      rejectedByServer: 0,
      rejectedLocally: 0,
      beaconAccepted: 0
    };
    const unsubscribe = deps.subscribeHidden(() => {
      onHidden();
    });
    function armTimer() {
      if (stopped || timer !== null || queue.length === 0 || inFlight) {
        return;
      }
      timer = deps.schedule(() => {
        timer = null;
        void flush();
      }, flushIntervalMs);
    }
    function clearTimer() {
      if (timer !== null) {
        deps.cancel(timer);
        timer = null;
      }
      if (delayTimer !== null) {
        deps.cancel(delayTimer);
        delayTimer = null;
      }
      const release = releaseDelay;
      releaseDelay = null;
      release?.();
    }
    function removeEvents(events) {
      const ids = new Set(events.map((event) => event.eventId));
      queue = queue.filter((event) => !ids.has(event.eventId));
    }
    function delay(ms) {
      return new Promise((resolve) => {
        releaseDelay = resolve;
        delayTimer = deps.schedule(() => {
          delayTimer = null;
          releaseDelay = null;
          resolve();
        }, ms);
      });
    }
    async function deliver(snapshot) {
      const body = JSON.stringify({ events: snapshot });
      let retries = 0;
      while (!stopped) {
        let result;
        try {
          result = await deps.send(deps.endpoint(), body);
        } catch {
          result = { ok: false, status: 0, received: null };
        }
        const acknowledged = result.ok && result.status === 200 && result.received === snapshot.length;
        if (acknowledged) {
          removeEvents(snapshot);
          return;
        }
        const transient = result.status === 0 || result.status === 408 || result.status === 429 || result.status >= 500;
        if (!transient) {
          stats.rejectedByServer += snapshot.length;
          removeEvents(snapshot);
          return;
        }
        if (retries >= maxRetries) {
          stats.droppedAfterRetry += snapshot.length;
          removeEvents(snapshot);
          return;
        }
        const wait = backoffBaseMs * 2 ** retries;
        retries += 1;
        await delay(wait);
      }
    }
    function flush() {
      if (stopped) {
        return Promise.resolve();
      }
      if (inFlight) {
        flushAgain = true;
        return inFlight;
      }
      if (queue.length === 0) {
        return Promise.resolve();
      }
      clearTimer();
      const snapshot = queue.slice(0, batchSize);
      inFlightIds = new Set(snapshot.map((event) => event.eventId));
      const run = deliver(snapshot).finally(() => {
        inFlight = null;
        inFlightIds = /* @__PURE__ */ new Set();
        if (stopped) {
          return;
        }
        if (flushAgain || queue.length >= batchSize) {
          flushAgain = false;
          void flush();
          return;
        }
        if (queue.length > 0) {
          armTimer();
        }
      });
      inFlight = run;
      return run;
    }
    function onHidden() {
      if (stopped || queue.length === 0) {
        return;
      }
      const pending = queue.filter((event) => !inFlightIds.has(event.eventId)).slice(0, batchSize);
      if (pending.length === 0) {
        return;
      }
      const body = JSON.stringify({ events: pending });
      if (body.length > maxBeaconBytes) {
        void flush();
        return;
      }
      let accepted = false;
      try {
        accepted = deps.sendBeacon(deps.endpoint(), body);
      } catch {
        accepted = false;
      }
      if (accepted) {
        stats.beaconAccepted += pending.length;
        removeEvents(pending);
        if (queue.length === 0) {
          clearTimer();
        }
        return;
      }
      void flush();
    }
    return {
      track(eventType, properties) {
        if (stopped) {
          return;
        }
        try {
          const event = buildTelemetryEvent({
            eventType,
            properties,
            nowMs: deps.now(),
            newId: deps.newId,
            sessionId: deps.getSessionId(),
            userId: deps.getUserId()
          });
          if (!event) {
            stats.rejectedLocally += 1;
            return;
          }
          queue.push(event);
          if (queue.length >= batchSize) {
            void flush();
            return;
          }
          armTimer();
        } catch {
          stats.rejectedLocally += 1;
        }
      },
      flush,
      stop() {
        stopped = true;
        clearTimer();
        unsubscribe();
      },
      queueLength() {
        return queue.length;
      },
      stats() {
        return { ...stats };
      }
    };
  }

  // packages/telemetry/src/browser.ts
  var DEFAULT_TELEMETRY_ENDPOINT = "http://localhost:8000/telemetry/events";
  var SESSION_KEY = "brasaland.telemetry.session_id";
  var USER_KEY = "brasaland.telemetry.user_id";
  function globals() {
    return globalThis;
  }
  function readTelemetryEndpoint(source) {
    const value = source?.NEXT_PUBLIC_TELEMETRY_ENDPOINT?.trim();
    return value ? value : DEFAULT_TELEMETRY_ENDPOINT;
  }
  function endpointFromGlobals() {
    const current = globals();
    return readTelemetryEndpoint({
      NEXT_PUBLIC_TELEMETRY_ENDPOINT: current.process?.env?.NEXT_PUBLIC_TELEMETRY_ENDPOINT || current.NEXT_PUBLIC_TELEMETRY_ENDPOINT
    });
  }
  function storage() {
    try {
      return globals().sessionStorage ?? null;
    } catch {
      return null;
    }
  }
  var memorySessionId = null;
  var memoryUserId = null;
  function newUuid() {
    const uuid = globals().crypto?.randomUUID?.();
    if (uuid) {
      return uuid;
    }
    return "00000000-0000-4000-8000-000000000000";
  }
  function browserSessionId() {
    const store = storage();
    const existing = store?.getItem(SESSION_KEY) ?? memorySessionId;
    if (existing) {
      return existing;
    }
    const created = newUuid();
    memorySessionId = created;
    try {
      store?.setItem(SESSION_KEY, created);
    } catch {
      memorySessionId = created;
    }
    return created;
  }
  function browserUserId() {
    const store = storage();
    const existing = store?.getItem(USER_KEY) ?? memoryUserId;
    if (existing) {
      return existing;
    }
    if (!globals().BrasalandSession?.hasAccessToken?.()) {
      return null;
    }
    const created = newUuid();
    memoryUserId = created;
    try {
      store?.setItem(USER_KEY, created);
    } catch {
      memoryUserId = created;
    }
    return created;
  }
  function createBrowserTelemetry() {
    return createTelemetryService({
      now: () => Date.now(),
      newId: () => newUuid(),
      getSessionId: () => browserSessionId(),
      getUserId: () => browserUserId(),
      endpoint: () => endpointFromGlobals(),
      async send(url, body) {
        const response = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body
        });
        let received = null;
        try {
          const payload = await response.json();
          if (typeof payload.received === "number") {
            received = payload.received;
          }
        } catch {
          received = null;
        }
        return { ok: response.ok, status: response.status, received };
      },
      sendBeacon(url, body) {
        const beacon = globals().navigator?.sendBeacon;
        if (!beacon) {
          return false;
        }
        const blob = new Blob([body], { type: "application/json" });
        return beacon(url, blob);
      },
      schedule(fn, ms) {
        return setTimeout(fn, ms);
      },
      cancel(id2) {
        clearTimeout(id2);
      },
      subscribeHidden(listener) {
        const documentRef = globals().document;
        if (!documentRef) {
          return () => void 0;
        }
        const onChange = () => {
          if (documentRef.visibilityState === "hidden") {
            listener();
          }
        };
        documentRef.addEventListener("visibilitychange", onChange);
        return () => documentRef.removeEventListener("visibilitychange", onChange);
      }
    });
  }
  var browserService = null;
  function shared() {
    if (!browserService) {
      browserService = createBrowserTelemetry();
    }
    return browserService;
  }
  function track(eventType, properties) {
    shared().track(eventType, properties);
  }

  // packages/telemetry/src/backoffice.ts
  function safeTrack(eventType, properties) {
    try {
      track(eventType, properties);
    } catch {
    }
  }
  function connectionType() {
    const current = globalThis;
    return current.navigator?.connection?.type;
  }
  function durationMs() {
    const current = globalThis;
    const navigation = current.performance?.getEntriesByType("navigation")[0];
    if (navigation && typeof navigation.duration === "number" && navigation.duration > 0) {
      return navigation.duration;
    }
    const elapsed = current.performance?.now();
    if (typeof elapsed === "number" && Number.isFinite(elapsed) && elapsed > 0) {
      return elapsed;
    }
    return 0;
  }
  function installBackofficeTelemetry(trackFn = safeTrack) {
    const current = globalThis;
    let storage2 = null;
    try {
      storage2 = current.sessionStorage ?? null;
    } catch {
      storage2 = null;
    }
    const hooks = createCaptureHooks(trackFn, storage2);
    const client = {
      ...hooks,
      noteCurrentPage() {
        if (current.__brasalandPageNoted) {
          return;
        }
        current.__brasalandPageNoted = true;
        const page2 = current.document?.body?.dataset?.telemetryPage;
        observeCurrentPage(hooks, {
          page: page2,
          durationMs: 0,
          includeLoad: false
        });
        const sendLoad = () => {
          observeCurrentPage(hooks, {
            page: page2,
            durationMs: durationMs(),
            connection: connectionType(),
            includeView: false
          });
        };
        const documentRef = current.document;
        if (!documentRef || documentRef.readyState === "complete") {
          sendLoad();
          return;
        }
        window.addEventListener("load", sendLoad, { once: true });
      }
    };
    current.BrasalandTelemetry = client;
    return client;
  }
  installBackofficeTelemetry();
})();
