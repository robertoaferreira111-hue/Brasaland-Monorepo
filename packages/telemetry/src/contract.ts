/**
 * Event names and property allowlists from docs/telemetry/event-schemas.json.
 * schemaVersion is the catalog constant 1.0.0.
 */

export const SCHEMA_VERSION = "1.0.0" as const;

export const TELEMETRY_EVENTS = [
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
  "page_load_completed",
] as const;

export type TelemetryEventName = (typeof TELEMETRY_EVENTS)[number];

export type Country = "CO" | "US";
export type Currency = "COP" | "USD";
export type ProductCategory =
  | "protein"
  | "vegetable"
  | "sauce"
  | "beverage"
  | "packaging"
  | "cleaning";
export type Unit = "kg" | "unit" | "liter";
export type WasteReason = "expired" | "kitchen_error" | "theft_suspected";
export type OpsPage =
  | "login"
  | "inbound_orders"
  | "outbound_orders"
  | "stock"
  | "products"
  | "suppliers"
  | "account";
export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface InventoryCore {
  location_id: string;
  country: Country;
  product_id: string;
  product_category: ProductCategory;
  quantity: number;
  unit: Unit;
  currency: Currency;
}

export interface TelemetryProperties {
  inbound_order_created: InventoryCore & {
    supplier_id: string;
    unit_cost: number;
    inbound_order_id: string;
  };
  outbound_order_created: InventoryCore & {
    outbound_order_id: string;
    reason: "prep_consumption";
  };
  stock_waste_registered: InventoryCore & {
    outbound_order_id: string;
    reason: WasteReason;
  };
  stock_threshold_triggered: InventoryCore & {
    minimum_quantity: number;
  };
  direct_stock_edit_rejected: InventoryCore & {
    rejection_code: "direct_edit_forbidden";
  };
  ingredient_price_variance_detected: InventoryCore & {
    supplier_id: string;
    unit_cost: number;
    historical_unit_cost: number;
    variance_pct: number;
    variance_threshold_pct: number;
    inbound_order_id: string;
  };
  product_validation_failed: {
    error_code:
      | "missing_required_field"
      | "invalid_unit"
      | "invalid_category"
      | "invalid_quantity"
      | "invalid_currency"
      | "invalid_country";
    field:
      | "product_id"
      | "product_category"
      | "quantity"
      | "unit"
      | "currency"
      | "country"
      | "location_id"
      | "supplier_id"
      | "reason";
    entity: "product" | "inbound_order" | "outbound_order";
    product_id?: string;
    location_id?: string;
    country?: Country;
  };
  user_logged_in: { auth_method: "password" };
  user_login_failed: {
    error_code: "invalid_credentials" | "validation_error" | "account_locked";
    attempt_bucket: "1" | "2-5" | "6+";
  };
  user_logged_out: {
    reason: "user_action" | "token_revoked" | "session_expired";
  };
  page_viewed: { page: OpsPage; referrer_page?: OpsPage | null };
  workflow_abandoned: {
    workflow: "inbound_order_create" | "outbound_order_create" | "waste_register";
    step_reached:
      | "form_opened"
      | "product_selected"
      | "quantity_entered"
      | "review"
      | "submit_attempted";
    duration_ms: number;
    location_id?: string;
    country?: Country;
  };
  api_request_completed: {
    route_template: string;
    method: HttpMethod;
    status_code: number;
    duration_ms: number;
  };
  api_request_failed: {
    route_template: string;
    method: HttpMethod;
    status_code: number;
    error_code:
      | "unauthorized"
      | "forbidden"
      | "not_found"
      | "validation_error"
      | "conflict"
      | "internal_error"
      | "timeout"
      | "network_error";
    duration_ms: number;
  };
  page_load_completed: {
    page: OpsPage;
    duration_ms: number;
    connection_type?: "wifi" | "cellular" | "ethernet" | "unknown";
  };
}

export interface TelemetryEvent {
  eventId: string;
  timestamp: string;
  sessionId: string;
  userId: string | null;
  event_type: TelemetryEventName;
  entity_action: TelemetryEventName;
  schemaVersion: typeof SCHEMA_VERSION;
  requestId: string;
  properties: Record<string, unknown>;
}

export interface TelemetryBatchBody {
  events: TelemetryEvent[];
}

type FieldKind = "string" | "number" | "integer" | "country" | "currency";

interface FieldRule {
  kind: FieldKind;
  min?: number;
  max?: number;
  exclusiveMin?: number;
  values?: readonly string[];
}

interface EventRule {
  required: readonly string[];
  optional: readonly string[];
  fields: Record<string, FieldRule>;
  currencyPair?: boolean;
}

const country: FieldRule = { kind: "country", values: ["CO", "US"] };
const currency: FieldRule = { kind: "currency", values: ["COP", "USD"] };
const category: FieldRule = {
  kind: "string",
  values: ["protein", "vegetable", "sauce", "beverage", "packaging", "cleaning"],
};
const unit: FieldRule = { kind: "string", values: ["kg", "unit", "liter"] };
const id: FieldRule = { kind: "string" };
const positive: FieldRule = { kind: "number", exclusiveMin: 0 };
const nonNegative: FieldRule = { kind: "number", min: 0 };
const anyNumber: FieldRule = { kind: "number" };
const page: FieldRule = {
  kind: "string",
  values: [
    "login",
    "inbound_orders",
    "outbound_orders",
    "stock",
    "products",
    "suppliers",
    "account",
  ],
};
const method: FieldRule = {
  kind: "string",
  values: ["GET", "POST", "PUT", "PATCH", "DELETE"],
};

const inventoryFields: Record<string, FieldRule> = {
  location_id: id,
  country,
  product_id: id,
  product_category: category,
  quantity: positive,
  unit,
  currency,
};

const inventoryRequired = [
  "location_id",
  "country",
  "product_id",
  "product_category",
  "quantity",
  "unit",
  "currency",
] as const;

function inventory(extraRequired: string[], extraFields: Record<string, FieldRule>, quantity: FieldRule = positive): EventRule {
  return {
    required: [...inventoryRequired, ...extraRequired],
    optional: [],
    currencyPair: true,
    fields: { ...inventoryFields, quantity, ...extraFields },
  };
}

const RULES: Record<TelemetryEventName, EventRule> = {
  inbound_order_created: inventory(
    ["supplier_id", "unit_cost", "inbound_order_id"],
    { supplier_id: id, unit_cost: positive, inbound_order_id: id },
  ),
  outbound_order_created: inventory(
    ["outbound_order_id", "reason"],
    { outbound_order_id: id, reason: { kind: "string", values: ["prep_consumption"] } },
  ),
  stock_waste_registered: inventory(
    ["outbound_order_id", "reason"],
    {
      outbound_order_id: id,
      reason: { kind: "string", values: ["expired", "kitchen_error", "theft_suspected"] },
    },
  ),
  stock_threshold_triggered: inventory(
    ["minimum_quantity"],
    { minimum_quantity: positive },
    nonNegative,
  ),
  direct_stock_edit_rejected: inventory(
    ["rejection_code"],
    { rejection_code: { kind: "string", values: ["direct_edit_forbidden"] } },
    anyNumber,
  ),
  ingredient_price_variance_detected: inventory(
    [
      "supplier_id",
      "unit_cost",
      "historical_unit_cost",
      "variance_pct",
      "variance_threshold_pct",
      "inbound_order_id",
    ],
    {
      supplier_id: id,
      unit_cost: positive,
      historical_unit_cost: positive,
      variance_pct: anyNumber,
      variance_threshold_pct: positive,
      inbound_order_id: id,
    },
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
          "invalid_country",
        ],
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
          "reason",
        ],
      },
      entity: { kind: "string", values: ["product", "inbound_order", "outbound_order"] },
      product_id: id,
      location_id: id,
      country,
    },
  },
  user_logged_in: {
    required: ["auth_method"],
    optional: [],
    fields: { auth_method: { kind: "string", values: ["password"] } },
  },
  user_login_failed: {
    required: ["error_code", "attempt_bucket"],
    optional: [],
    fields: {
      error_code: {
        kind: "string",
        values: ["invalid_credentials", "validation_error", "account_locked"],
      },
      attempt_bucket: { kind: "string", values: ["1", "2-5", "6+"] },
    },
  },
  user_logged_out: {
    required: ["reason"],
    optional: [],
    fields: {
      reason: { kind: "string", values: ["user_action", "token_revoked", "session_expired"] },
    },
  },
  page_viewed: {
    required: ["page"],
    optional: ["referrer_page"],
    fields: { page, referrer_page: page },
  },
  workflow_abandoned: {
    required: ["workflow", "step_reached", "duration_ms"],
    optional: ["location_id", "country"],
    fields: {
      workflow: {
        kind: "string",
        values: ["inbound_order_create", "outbound_order_create", "waste_register"],
      },
      step_reached: {
        kind: "string",
        values: ["form_opened", "product_selected", "quantity_entered", "review", "submit_attempted"],
      },
      duration_ms: nonNegative,
      location_id: id,
      country,
    },
  },
  api_request_completed: {
    required: ["route_template", "method", "status_code", "duration_ms"],
    optional: [],
    fields: {
      route_template: id,
      method,
      status_code: { kind: "integer", min: 200, max: 299 },
      duration_ms: nonNegative,
    },
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
          "network_error",
        ],
      },
      duration_ms: nonNegative,
    },
  },
  page_load_completed: {
    required: ["page", "duration_ms"],
    optional: ["connection_type"],
    fields: {
      page,
      duration_ms: nonNegative,
      connection_type: { kind: "string", values: ["wifi", "cellular", "ethernet", "unknown"] },
    },
  },
};

function isTelemetryEventName(value: string): value is TelemetryEventName {
  return (TELEMETRY_EVENTS as readonly string[]).includes(value);
}

function fieldOk(value: unknown, rule: FieldRule, allowNull: boolean): boolean {
  if (value === null) {
    return allowNull;
  }
  if (rule.kind === "string" || rule.kind === "country" || rule.kind === "currency") {
    if (typeof value !== "string" || value.trim() === "") {
      return false;
    }
    return rule.values === undefined || rule.values.includes(value);
  }
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return false;
  }
  if (rule.kind === "integer" && !Number.isInteger(value)) {
    return false;
  }
  if (rule.min !== undefined && value < rule.min) {
    return false;
  }
  if (rule.max !== undefined && value > rule.max) {
    return false;
  }
  if (rule.exclusiveMin !== undefined && !(value > rule.exclusiveMin)) {
    return false;
  }
  return true;
}

export function allowlistedProperties(
  eventType: string,
  properties: object,
): Record<string, unknown> | null {
  if (!isTelemetryEventName(eventType)) {
    return null;
  }
  const rule = RULES[eventType];
  const record = properties as Record<string, unknown>;
  const allowed = new Set([...rule.required, ...rule.optional]);
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
  const copy: Record<string, unknown> = {};
  for (const key of [...rule.required, ...rule.optional]) {
    if (Object.prototype.hasOwnProperty.call(record, key)) {
      copy[key] = record[key];
    }
  }
  return copy;
}

function currencyMatchesCountry(record: Record<string, unknown>): boolean {
  if (record.country === "CO") {
    return record.currency === "COP";
  }
  if (record.country === "US") {
    return record.currency === "USD";
  }
  return false;
}
