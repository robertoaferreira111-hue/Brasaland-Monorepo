import assert from "node:assert/strict";
import test from "node:test";
import {
  ADDRESS_ERROR,
  NAME_ERROR,
  PHONE_ERROR,
  mergeSavedProfile,
  profileUpdatePayload,
  readProfile,
} from "./profile.ts";
import { isProtectedPath, PROTECTED_PATHS, PUBLIC_AUTH_PATHS } from "./routes.ts";

test("only /account is protected in this app", () => {
  assert.deepEqual([...PROTECTED_PATHS], ["/account"]);
  assert.deepEqual([...PUBLIC_AUTH_PATHS], ["/login", "/register"]);
  assert.equal(isProtectedPath("/account"), true);
  assert.equal(isProtectedPath("/account/settings"), true);
  assert.equal(isProtectedPath("/login"), false);
  assert.equal(isProtectedPath("/register"), false);
  assert.equal(isProtectedPath("/"), false);
});

test("readProfile keeps root email when contact fields are nested", () => {
  assert.deepEqual(
    readProfile({
      email: "staff@brasaland.com",
      profile: {
        name: "Camila Ospina",
        phone: "+57 300 123 4567",
        address: "Medellin",
      },
    }),
    {
      email: "staff@brasaland.com",
      name: "Camila Ospina",
      phone: "+57 300 123 4567",
      address: "Medellin",
    },
  );
});

test("readProfile accepts a flat /auth/me body", () => {
  assert.deepEqual(
    readProfile({
      email: "a@b.com",
      name: "Lucía",
      phone: "+1 305 123 4567",
      address: "Miami",
    }),
    {
      email: "a@b.com",
      name: "Lucía",
      phone: "+1 305 123 4567",
      address: "Miami",
    },
  );
});

test("profile update requires name, phone, and address", () => {
  assert.equal(profileUpdatePayload({ name: "", phone: "1", address: "a" }), null);
  assert.equal(profileUpdatePayload({ name: "n", phone: "", address: "a" }), null);
  assert.equal(profileUpdatePayload({ name: "n", phone: "1", address: "" }), null);
  assert.deepEqual(
    profileUpdatePayload({
      name: " Camila ",
      phone: " +57 300 ",
      address: " El Poblado ",
    }),
    {
      name: "Camila",
      phone: "+57 300",
      address: "El Poblado",
    },
  );
  assert.equal(NAME_ERROR.length > 0, true);
  assert.equal(PHONE_ERROR.length > 0, true);
  assert.equal(ADDRESS_ERROR.length > 0, true);
});

test("saved profile keeps previous email when the PUT body omits it", () => {
  assert.deepEqual(
    mergeSavedProfile(
      { email: "", name: "Camila", phone: "+57", address: "Medellin" },
      { name: "Camila", phone: "+57", address: "Medellin" },
      "staff@brasaland.com",
    ),
    {
      email: "staff@brasaland.com",
      name: "Camila",
      phone: "+57",
      address: "Medellin",
    },
  );
});
