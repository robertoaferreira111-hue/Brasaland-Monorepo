import { USER_MESSAGES, normalizeSupplier } from "./supplierErrors.mjs";
import {
  requestJsonMutation,
  requestSupplierList,
  withLoadingState,
} from "./supplierRequests.mjs";

function resolveApiBase() {
  const override = new URLSearchParams(window.location.search).get("api");
  if (override) {
    return override.replace(/\/+$/, "");
  }
  const { hostname, protocol } = window.location;
  if (hostname.endsWith(".app.github.dev")) {
    const apiHost = hostname.replace(/-\d+(?=\.app\.github\.dev$)/, "-8000");
    return `${protocol}//${apiHost}`;
  }
  return "http://127.0.0.1:8000";
}

const API_BASE = resolveApiBase();

const CATEGORIES = [
  "carne",
  "verduras_y_hortalizas",
  "salsas_y_condimentos",
  "bebidas",
  "packaging",
  "productos_limpieza",
  "lacteos",
  "carbon_y_combustible",
];

const COUNTRIES = ["Colombia", "USA"];
const STATUSES = ["active", "suspended"];
const CURRENCY_BY_COUNTRY = {
  Colombia: "COP",
  USA: "USD",
};

const filtersForm = document.getElementById("filters");
const countryFilter = document.getElementById("filter-country");
const categoryFilter = document.getElementById("filter-category");
const statusFilter = document.getElementById("filter-status");
const listStatus = document.getElementById("list-status");
const listErrorPanel = document.getElementById("list-error-panel");
const listError = document.getElementById("list-error");
const listRetry = document.getElementById("list-retry");
const emptyState = document.getElementById("empty-state");
const tableWrap = document.getElementById("table-wrap");
const supplierRows = document.getElementById("supplier-rows");
const registerForm = document.getElementById("register-form");
const registerCountry = document.getElementById("register-country");
const registerCurrency = document.getElementById("register-currency");
const registerStatus = document.getElementById("register-status");
const categoryChoices = document.getElementById("category-choices");
const registerSubmit = document.getElementById("register-submit");
const formError = document.getElementById("form-error");
const formSuccess = document.getElementById("form-success");
const formErrorActions = document.getElementById("form-error-actions");
const formRetry = document.getElementById("form-retry");

let loadedSuppliers = [];
let listRequestActive = false;

function fillSelect(select, values, allLabel) {
  select.replaceChildren();
  const allOption = document.createElement("option");
  allOption.value = "";
  allOption.textContent = allLabel;
  select.append(allOption);
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.append(option);
  }
}

function fillRequiredSelect(select, values) {
  select.replaceChildren();
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.append(option);
  }
}

function buildCategoryChoices() {
  categoryChoices.replaceChildren();
  for (const category of CATEGORIES) {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.name = "categories";
    input.value = category;
    label.append(input, document.createTextNode(category));
    categoryChoices.append(label);
  }
}

function syncCurrency() {
  registerCurrency.value = CURRENCY_BY_COUNTRY[registerCountry.value];
}

function showMessage(element, text) {
  element.hidden = !text;
  element.textContent = text || "";
}

function setListError(message) {
  showMessage(listError, message);
  listErrorPanel.hidden = !message;
}

function setFormError(message) {
  showMessage(formError, message);
  formErrorActions.hidden = !message;
}

function setFiltersDisabled(disabled) {
  for (const control of filtersForm.querySelectorAll("select")) {
    control.disabled = disabled;
  }
}

function setListLoading(isLoading) {
  listRequestActive = isLoading;
  setFiltersDisabled(isLoading);
  tableWrap.setAttribute("aria-busy", isLoading ? "true" : "false");
  if (isLoading) {
    listStatus.textContent = "Loading suppliers…";
  }
}

function visibleSuppliers() {
  const status = statusFilter.value;
  if (!status) {
    return loadedSuppliers;
  }
  return loadedSuppliers.filter((supplier) => supplier.status === status);
}

function formatTimestamp(value) {
  if (value == null || value === "") {
    return "";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }
  return parsed.toLocaleString();
}

function renderSuppliers(options = {}) {
  if (options.failed) {
    supplierRows.replaceChildren();
    emptyState.hidden = true;
    tableWrap.hidden = true;
    if (!listRequestActive) {
      listStatus.textContent = "";
    }
    return;
  }

  const suppliers = visibleSuppliers();
  supplierRows.replaceChildren();
  const hasRows = suppliers.length > 0;
  emptyState.hidden = hasRows;
  tableWrap.hidden = !hasRows;

  for (const supplier of suppliers) {
    const row = document.createElement("tr");
    if (supplier.status === "suspended") {
      row.classList.add("is-suspended");
    }

    const displayName = supplier.name || "Unnamed supplier";
    row.append(
      cell(displayName),
      cell(supplier.country),
      cell((supplier.categories ?? []).join(", ")),
      rateCell(supplier, displayName),
      cell(supplier.currency),
      statusCell(supplier),
      cell(supplier.contact_email ?? ""),
      cell(supplier.notes ?? ""),
      cell(formatTimestamp(supplier.updated_at)),
    );
    supplierRows.append(row);
  }

  const count = suppliers.length;
  listStatus.textContent =
    count === 1 ? "1 supplier shown." : `${count} suppliers shown.`;
}

function cell(text) {
  const item = document.createElement("td");
  item.textContent = text;
  return item;
}

function attachRowRecovery(container, onRetry) {
  const actions = document.createElement("div");
  actions.className = "row-recovery";
  actions.hidden = true;

  const retry = document.createElement("button");
  retry.type = "button";
  retry.className = "button-secondary";
  retry.textContent = "Try again";
  retry.addEventListener("click", () => {
    onRetry();
  });

  const support = document.createElement("p");
  support.className = "recovery-hint";
  support.textContent = "If this keeps happening, contact support.";

  actions.append(retry, support);
  container.append(actions);
  return actions;
}

function showRowFailure(error, recovery, message) {
  showMessage(error, message);
  recovery.hidden = !message;
}

function rateCell(supplier, displayName) {
  const item = document.createElement("td");
  const form = document.createElement("form");
  form.className = "rate-form";
  form.dataset.rateForm = String(supplier.id);

  const input = document.createElement("input");
  input.type = "number";
  input.step = "any";
  input.name = "rate_per_unit";
  input.required = true;
  input.value = supplier.rate_per_unit;
  input.setAttribute("aria-label", `rate_per_unit for ${displayName}`);

  const button = document.createElement("button");
  button.type = "submit";
  button.textContent = "Update rate";
  button.dataset.defaultLabel = "Update rate";

  const error = document.createElement("p");
  error.className = "row-error";
  error.hidden = true;

  form.append(input, button, error);
  const recovery = attachRowRecovery(form, () => {
    updateRate(form);
  });
  item.append(form);
  form._rowError = error;
  form._rowRecovery = recovery;
  return item;
}

function statusCell(supplier) {
  const item = document.createElement("td");
  const actions = document.createElement("div");
  actions.className = "row-actions";

  const badge = document.createElement("span");
  badge.className = `badge badge-${supplier.status}`;
  badge.textContent = supplier.status;

  const button = document.createElement("button");
  button.type = "button";
  button.dataset.statusToggle = String(supplier.id);
  const nextStatus = supplier.status === "active" ? "suspended" : "active";
  button.dataset.nextStatus = nextStatus;
  button.dataset.defaultLabel =
    nextStatus === "suspended" ? "Suspend" : "Activate";
  button.textContent = button.dataset.defaultLabel;

  const error = document.createElement("p");
  error.className = "row-error";
  error.dataset.statusError = String(supplier.id);
  error.hidden = true;

  actions.append(badge, button, error);
  const recovery = attachRowRecovery(actions, () => {
    updateStatus(button);
  });
  item.append(actions);
  button._rowError = error;
  button._rowRecovery = recovery;
  return item;
}

async function loadSuppliers() {
  setListError("");

  const params = new URLSearchParams();
  if (countryFilter.value) {
    params.set("country", countryFilter.value);
  }
  if (categoryFilter.value) {
    params.set("category", categoryFilter.value);
  }
  const query = params.toString();
  const url = query ? `${API_BASE}/suppliers?${query}` : `${API_BASE}/suppliers`;

  const result = await withLoadingState(setListLoading, () =>
    requestSupplierList(url),
  );

  if (result.status !== "fulfilled") {
    loadedSuppliers = [];
    renderSuppliers({ failed: true });
    setListError(result.message);
    listStatus.textContent = "";
    return;
  }

  loadedSuppliers = result.suppliers;
  setListError("");
  renderSuppliers();
}

function replaceSupplier(updated) {
  const normalized = normalizeSupplier(updated);
  if (!normalized) {
    setListError(USER_MESSAGES.malformed);
    return;
  }
  const index = loadedSuppliers.findIndex(
    (supplier) => supplier.id === normalized.id,
  );
  if (index === -1) {
    loadedSuppliers.push(normalized);
  } else {
    loadedSuppliers[index] = normalized;
  }
  renderSuppliers();
}

function setBusyButton(button, busy, busyLabel) {
  if (!button) {
    return;
  }
  button.disabled = busy;
  button.textContent = busy
    ? busyLabel
    : button.dataset.defaultLabel || button.textContent;
}

async function updateRate(form) {
  const supplierId = form.dataset.rateForm;
  const error = form._rowError || form.querySelector(".row-error");
  const recovery = form._rowRecovery || form.querySelector(".row-recovery");
  const button = form.querySelector('button[type="submit"]');
  const rate = Number(form.rate_per_unit.value);
  showRowFailure(error, recovery, "");
  setBusyButton(button, true, "Saving…");
  try {
    const result = await requestJsonMutation(
      `${API_BASE}/suppliers/${supplierId}/rate`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rate_per_unit: rate }),
      },
    );
    if (result.status !== "fulfilled") {
      showRowFailure(error, recovery, result.message);
      return;
    }
    replaceSupplier(result.data);
    showMessage(formSuccess, "Rate updated.");
    setFormError("");
  } finally {
    setBusyButton(button, false);
  }
}

async function updateStatus(button) {
  const supplierId = button.dataset.statusToggle;
  const nextStatus = button.dataset.nextStatus;
  const error =
    button._rowError ||
    button.parentElement.querySelector(".row-error");
  const recovery =
    button._rowRecovery ||
    button.parentElement.querySelector(".row-recovery");
  showRowFailure(error, recovery, "");
  setBusyButton(button, true, "Saving…");
  try {
    const result = await requestJsonMutation(
      `${API_BASE}/suppliers/${supplierId}/status`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: nextStatus }),
      },
    );
    if (result.status !== "fulfilled") {
      showRowFailure(error, recovery, result.message);
      return;
    }
    replaceSupplier(result.data);
    showMessage(formSuccess, `Status updated to ${result.data.status}.`);
    setFormError("");
  } finally {
    setBusyButton(button, false);
  }
}

async function registerSupplier(event) {
  event.preventDefault();
  setFormError("");
  showMessage(formSuccess, "");

  const selectedCategories = [
    ...registerForm.querySelectorAll('input[name="categories"]:checked'),
  ].map((input) => input.value);

  if (selectedCategories.length === 0) {
    setFormError("Select at least one category.");
    return;
  }

  const payload = {
    name: registerForm.name.value.trim(),
    country: registerForm.country.value,
    categories: selectedCategories,
    rate_per_unit: Number(registerForm.rate_per_unit.value),
    currency: registerCurrency.value,
    status: registerForm.status.value,
  };
  const email = registerForm.contact_email.value.trim();
  const notes = registerForm.notes.value.trim();
  if (email) {
    payload.contact_email = email;
  }
  if (notes) {
    payload.notes = notes;
  }

  registerSubmit.dataset.defaultLabel =
    registerSubmit.dataset.defaultLabel || registerSubmit.textContent;
  setBusyButton(registerSubmit, true, "Registering…");
  try {
    const result = await requestJsonMutation(`${API_BASE}/suppliers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (result.status !== "fulfilled") {
      setFormError(result.message);
      return;
    }
    registerForm.reset();
    registerCountry.value = "Colombia";
    registerStatus.value = "active";
    syncCurrency();
    showMessage(
      formSuccess,
      `${result.data.name || "Supplier"} was registered.`,
    );
    setFormError("");
    await loadSuppliers();
  } finally {
    setBusyButton(registerSubmit, false);
  }
}

function setupNavigation() {
  const toggle = document.getElementById("nav-toggle");
  const nav = document.getElementById("site-nav");
  toggle.addEventListener("click", () => {
    const open = nav.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", String(open));
    toggle.textContent = open ? "Close navigation" : "Open navigation";
  });
}

fillSelect(countryFilter, COUNTRIES, "All countries");
fillSelect(categoryFilter, CATEGORIES, "All categories");
fillSelect(statusFilter, STATUSES, "All statuses");
fillRequiredSelect(registerCountry, COUNTRIES);
fillRequiredSelect(registerStatus, STATUSES);
buildCategoryChoices();
syncCurrency();
setupNavigation();

registerCountry.addEventListener("change", syncCurrency);
filtersForm.addEventListener("submit", (event) => event.preventDefault());
filtersForm.addEventListener("change", (event) => {
  if (event.target === statusFilter) {
    renderSuppliers();
    return;
  }
  loadSuppliers();
});
registerForm.addEventListener("submit", registerSupplier);
listRetry.addEventListener("click", () => {
  loadSuppliers();
});
formRetry.addEventListener("click", () => {
  registerForm.requestSubmit();
});
supplierRows.addEventListener("submit", (event) => {
  const form = event.target.closest("[data-rate-form]");
  if (!form) {
    return;
  }
  event.preventDefault();
  updateRate(form);
});
supplierRows.addEventListener("click", (event) => {
  const button = event.target.closest("[data-status-toggle]");
  if (!button) {
    return;
  }
  updateStatus(button);
});

loadSuppliers();
