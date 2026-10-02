const CITIES = {
  Colombia: ["Medellín", "Bogotá", "Cali"],
  "United States": ["Miami", "Orlando"],
}

const LOCATIONS = {
  Medellín: ["Brasaland El Poblado", "Brasaland Laureles", "Brasaland Envigado", "Brasaland Sabaneta"],
  Bogotá: ["Brasaland Usaquén", "Brasaland Chapinero", "Brasaland Zona Rosa"],
  Cali: ["Brasaland Granada", "Brasaland Ciudad Jardín", "Brasaland Unicentro"],
  Miami: ["Brasaland Brickell", "Brasaland Coral Gables"],
  Orlando: ["Brasaland Downtown", "Brasaland International Drive"],
}

const SOURCES = ["Social media", "Recommendation", "Walked by", "Internet search", "Other"]

const ERRORS = {
  "full-name": "Enter your full name (first and last name)",
  email: "Enter a valid email (example: name@email.com)",
  phone: "Phone must include country code (example: +57 300 123 4567 or +1 305 123 4567)",
  country: "Select your country",
  city: "Select your city",
  source: "Tell us how you found Brasaland",
  "date-of-birth": "You must be 18 or older to register for Brasa Points",
  "accept-terms": "You must accept the Brasa Points program terms to continue",
}

const FIELD_ORDER = [
  "full-name",
  "email",
  "phone",
  "country",
  "city",
  "source",
  "date-of-birth",
  "accept-terms",
]

function valueOf(id) {
  const field = document.getElementById(id)
  if (!field) return ""
  if (field.type === "checkbox") return field.checked
  return field.value
}

function messageFor(id) {
  const country = valueOf("country")
  const city = valueOf("city")

  if (id === "full-name") {
    const words = String(valueOf(id)).trim().split(/\s+/).filter(Boolean)
    return words.length >= 2 ? "" : ERRORS[id]
  }

  if (id === "email") {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(valueOf(id)).trim()) ? "" : ERRORS[id]
  }

  if (id === "phone") {
    const compact = String(valueOf(id)).trim().replace(/[\s()-]/g, "")
    if (!compact) return ERRORS[id]
    if (country !== "Colombia" && country !== "United States") return ""
    const ok =
      country === "Colombia" ? /^\+57\d{8,12}$/.test(compact) : /^\+1\d{10}$/.test(compact)
    return ok ? "" : ERRORS[id]
  }

  if (id === "country") {
    return country === "Colombia" || country === "United States" ? "" : ERRORS[id]
  }

  if (id === "city") {
    const cities = CITIES[country] || []
    return city && cities.includes(city) ? "" : ERRORS[id]
  }

  if (id === "source") {
    return SOURCES.includes(valueOf(id)) ? "" : ERRORS[id]
  }

  if (id === "date-of-birth") {
    return isAtLeast18(String(valueOf(id))) ? "" : ERRORS[id]
  }

  if (id === "accept-terms") {
    return valueOf(id) ? "" : ERRORS[id]
  }

  return ""
}

function isAtLeast18(isoDate) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoDate)
  if (!match) return false
  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  const birth = new Date(year, month - 1, day)
  if (birth.getFullYear() !== year || birth.getMonth() !== month - 1 || birth.getDate() !== day) {
    return false
  }
  const today = new Date()
  const cutoff = new Date(today.getFullYear() - 18, today.getMonth(), today.getDate())
  return birth <= cutoff
}

function showError(id, message) {
  const field = document.getElementById(id)
  const error = document.getElementById(`${id}-error`)
  if (!field || !error) return
  error.textContent = message
  if (message) {
    field.setAttribute("aria-invalid", "true")
    field.setAttribute("aria-describedby", `${id}-error`)
  } else {
    field.removeAttribute("aria-invalid")
    field.removeAttribute("aria-describedby")
  }
}

function validateField(id) {
  const message = messageFor(id)
  showError(id, message)
  return message
}

function fillSelect(select, placeholder, options, selected) {
  select.replaceChildren()
  const empty = document.createElement("option")
  empty.value = ""
  empty.textContent = placeholder
  select.append(empty)
  for (const option of options) {
    const node = document.createElement("option")
    node.value = option
    node.textContent = option
    select.append(node)
  }
  select.value = options.includes(selected) ? selected : ""
}

function syncCities() {
  const country = valueOf("country")
  const city = document.getElementById("city")
  fillSelect(city, "Select your city", CITIES[country] || [], "")
  syncLocations()
}

function syncLocations() {
  const city = valueOf("city")
  const favorite = document.getElementById("favorite-location")
  fillSelect(favorite, "Select a location (optional)", LOCATIONS[city] || [], "")
}

let lastCountry = ""
let lastCity = ""

function validateAll() {
  let firstInvalid = ""
  for (const id of FIELD_ORDER) {
    const message = validateField(id)
    if (message && !firstInvalid) firstInvalid = id
  }
  return firstInvalid
}

function hideSuccess() {
  const success = document.getElementById("success")
  success.classList.add("hidden")
  document.getElementById("loyalty-form").classList.remove("hidden")
}

function resetForm() {
  const form = document.getElementById("loyalty-form")
  form.reset()
  lastCountry = ""
  lastCity = ""
  syncCities()
  for (const id of [...FIELD_ORDER, "favorite-location"]) showError(id, "")
  hideSuccess()
  document.getElementById("full-name").focus()
}

function onLiveEvent(event) {
  const field = event.target
  if (!(field instanceof HTMLElement) || !field.id || !ERRORS[field.id]) return
  if (field.id === "country") {
    const country = valueOf("country")
    if (country !== lastCountry) {
      const hadCity = Boolean(valueOf("city"))
      const phoneError = document.getElementById("phone-error")
      const shouldCheckPhone = Boolean(String(valueOf("phone")).trim()) || Boolean(phoneError.textContent)
      lastCountry = country
      lastCity = ""
      syncCities()
      if (hadCity) validateField("city")
      if (shouldCheckPhone) validateField("phone")
    }
    validateField("country")
    return
  }
  if (field.id === "city") {
    const city = valueOf("city")
    if (city !== lastCity) {
      lastCity = city
      syncLocations()
    }
    validateField("city")
    return
  }
  validateField(field.id)
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("loyalty-form")
  if (!form) return

  syncCities()

  form.addEventListener("submit", (event) => {
    event.preventDefault()
    const firstInvalid = validateAll()
    if (firstInvalid) {
      hideSuccess()
      document.getElementById(firstInvalid).focus()
      return
    }
    form.classList.add("hidden")
    const success = document.getElementById("success")
    success.classList.remove("hidden")
    success.focus()
  })

  form.addEventListener("blur", onLiveEvent, true)
  form.addEventListener("input", onLiveEvent)
  form.addEventListener("change", onLiveEvent)

  document.getElementById("clear-form").addEventListener("click", resetForm)
})
