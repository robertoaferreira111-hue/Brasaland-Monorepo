const session = window.BrasalandSession;

session.requireSession();

const form = document.getElementById("profile-form");
const formError = document.getElementById("form-error");
const formSuccess = document.getElementById("form-success");
const pageStatus = document.getElementById("page-status");

document.getElementById("directory-link").href = session.appHref("index.html");
document.getElementById("change-password-link").href = session.appHref(
  "account/change-password/",
);
document.getElementById("logout").addEventListener("click", () => {
  session.logout();
});

const toggle = document.getElementById("nav-toggle");
const nav = document.getElementById("site-nav");
toggle.addEventListener("click", () => {
  const open = nav.classList.toggle("is-open");
  toggle.setAttribute("aria-expanded", String(open));
  toggle.textContent = open ? "Close navigation" : "Open navigation";
});

function showMessage(element, text) {
  element.hidden = !text;
  element.textContent = text || "";
}

async function loadProfile() {
  pageStatus.textContent = "Loading profile…";
  try {
    const response = await session.apiFetch("/auth/me");
    if (!response.ok) {
      showMessage(formError, await session.errorText(response));
      pageStatus.textContent = "";
      return;
    }
    const profile = await response.json();
    document.getElementById("profile-email").value = profile.email;
    form.name.value = profile.name || "";
    form.phone.value = profile.phone || "";
    form.address.value = profile.address || "";
    form.hidden = false;
    pageStatus.textContent = "";
  } catch (error) {
    if (error instanceof Error && error.message === "Session expired") {
      return;
    }
    showMessage(formError, `The API is not reachable at ${session.API_BASE}.`);
    pageStatus.textContent = "";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  showMessage(formError, "");
  showMessage(formSuccess, "");
  const button = form.querySelector("button");
  button.disabled = true;
  try {
    const response = await session.apiFetch("/profiles/me", {
      method: "PUT",
      body: JSON.stringify({
        name: form.name.value,
        phone: form.phone.value,
        address: form.address.value,
      }),
    });
    if (!response.ok) {
      showMessage(formError, await session.errorText(response));
      return;
    }
    const profile = await response.json();
    form.name.value = profile.name;
    form.phone.value = profile.phone;
    form.address.value = profile.address;
    showMessage(formSuccess, "Profile saved.");
  } catch (error) {
    if (error instanceof Error && error.message === "Session expired") {
      return;
    }
    showMessage(formError, `The API is not reachable at ${session.API_BASE}.`);
  } finally {
    button.disabled = false;
  }
});

if (session.hasAccessToken()) {
  loadProfile();
}
