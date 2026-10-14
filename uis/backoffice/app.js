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
const listError = document.getElementById("list-error");
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

let loadedSuppliers = [];

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

function visibleSuppliers() {
  const status = statusFilter.value;
  if (!status) {
    return loadedSuppliers;
  }
  return loadedSuppliers.filter((supplier) => supplier.status === status);
}

function formatTimestamp(value) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return String(value ?? "");
  }
  return parsed.toLocaleString();
}

function renderSuppliers(options = {}) {
  if (options.failed) {
    supplierRows.replaceChildren();
    emptyState.hidden = true;
    tableWrap.hidden = true;
    listStatus.textContent = "";
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

    row.append(
      cell(supplier.name),
      cell(supplier.country),
      cell((supplier.categories || []).join(", ")),
      rateCell(supplier),
      cell(supplier.currency),
      statusCell(supplier),
      cell(supplier.contact_email || ""),
      cell(supplier.notes || ""),
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

function rateCell(supplier) {
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
  input.setAttribute("aria-label", `rate_per_unit for ${supplier.name}`);

  const button = document.createElement("button");
  button.type = "submit";
  button.textContent = "Update rate";

  const error = document.createElement("p");
  error.className = "row-error";
  error.hidden = true;

  form.append(input, button, error);
  item.append(form);
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
  button.textContent = nextStatus === "suspended" ? "Suspend" : "Activate";

  const error = document.createElement("p");
  error.className = "row-error";
  error.dataset.statusError = String(supplier.id);
  error.hidden = true;

  actions.append(badge, button, error);
  item.append(actions);
  return item;
}

async function readError(response) {
  try {
    const payload = await response.json();
    if (Array.isArray(payload.detail)) {
      return payload.detail
        .map((item) => {
          const location = Array.isArray(item.loc)
            ? item.loc.filter((part) => part !== "body").join(".")
            : "";
          return location ? `${location}: ${item.msg}` : item.msg;
        })
        .join(" ");
    }
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
  } catch (_error) {
    return `The supplier API returned HTTP ${response.status}.`;
  }
  return `The supplier API returned HTTP ${response.status}.`;
}

async function loadSuppliers() {
  showMessage(listError, "");
  listStatus.textContent = "Loading suppliers…";
  const params = new URLSearchParams();
  if (countryFilter.value) {
    params.set("country", countryFilter.value);
  }
  if (categoryFilter.value) {
    params.set("category", categoryFilter.value);
  }
  const query = params.toString();
  const url = query ? `${API_BASE}/suppliers?${query}` : `${API_BASE}/suppliers`;

  try {
    const response = await fetch(url);
    if (!response.ok) {
      loadedSuppliers = [];
      renderSuppliers({ failed: true });
      showMessage(listError, await readError(response));
      return;
    }
    loadedSuppliers = await response.json();
    renderSuppliers();
  } catch (_error) {
    loadedSuppliers = [];
    renderSuppliers({ failed: true });
    showMessage(
      listError,
      `The supplier API is not reachable at ${API_BASE}.`,
    );
  }
}

function replaceSupplier(updated) {
  const index = loadedSuppliers.findIndex((supplier) => supplier.id === updated.id);
  if (index === -1) {
    loadedSuppliers.push(updated);
  } else {
    loadedSuppliers[index] = updated;
  }
  renderSuppliers();
}

async function updateRate(form) {
  const supplierId = form.dataset.rateForm;
  const error = form.querySelector(".row-error");
  const button = form.querySelector("button");
  const rate = Number(form.rate_per_unit.value);
  showMessage(error, "");
  button.disabled = true;
  try {
    const response = await fetch(`${API_BASE}/suppliers/${supplierId}/rate`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rate_per_unit: rate }),
    });
    if (!response.ok) {
      showMessage(error, await readError(response));
      return;
    }
    replaceSupplier(await response.json());
    showMessage(formSuccess, "Rate updated.");
    showMessage(formError, "");
  } catch (_error) {
    showMessage(error, `The supplier API is not reachable at ${API_BASE}.`);
  } finally {
    button.disabled = false;
  }
}

async function updateStatus(button) {
  const supplierId = button.dataset.statusToggle;
  const nextStatus = button.dataset.nextStatus;
  const error = button.parentElement.querySelector(".row-error");
  showMessage(error, "");
  button.disabled = true;
  try {
    const response = await fetch(`${API_BASE}/suppliers/${supplierId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: nextStatus }),
    });
    if (!response.ok) {
      showMessage(error, await readError(response));
      return;
    }
    const updated = await response.json();
    replaceSupplier(updated);
    showMessage(formSuccess, `Status updated to ${updated.status}.`);
    showMessage(formError, "");
  } catch (_error) {
    showMessage(error, `The supplier API is not reachable at ${API_BASE}.`);
  } finally {
    button.disabled = false;
  }
}

async function registerSupplier(event) {
  event.preventDefault();
  showMessage(formError, "");
  showMessage(formSuccess, "");

  const selectedCategories = [
    ...registerForm.querySelectorAll('input[name="categories"]:checked'),
  ].map((input) => input.value);

  if (selectedCategories.length === 0) {
    showMessage(formError, "Select at least one category.");
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

  registerSubmit.disabled = true;
  try {
    const response = await fetch(`${API_BASE}/suppliers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      showMessage(formError, await readError(response));
      return;
    }
    const created = await response.json();
    registerForm.reset();
    registerCountry.value = "Colombia";
    registerStatus.value = "active";
    syncCurrency();
    showMessage(formSuccess, `${created.name} was registered.`);
    await loadSuppliers();
  } catch (_error) {
    showMessage(formError, `The supplier API is not reachable at ${API_BASE}.`);
  } finally {
    registerSubmit.disabled = false;
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
