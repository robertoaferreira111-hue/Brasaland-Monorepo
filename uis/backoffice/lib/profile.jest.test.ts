import {
  ADDRESS_ERROR,
  addressFieldError,
  mergeSavedProfile,
  NAME_ERROR,
  nameFieldError,
  PHONE_ERROR,
  phoneFieldError,
  profileUpdatePayload,
  readProfile,
} from "./profile";

describe("readProfile", () => {
  test("reads a flat profile body", () => {
    expect(
      readProfile({
        email: " staff@brasaland.com ",
        name: " Camila ",
        phone: " +57 300 ",
        address: " Medellin ",
      }),
    ).toEqual({
      email: "staff@brasaland.com",
      name: "Camila",
      phone: "+57 300",
      address: "Medellin",
    });
  });

  test("returns an empty profile when the body is not a record", () => {
    expect(readProfile(null)).toEqual({
      email: "",
      name: "",
      phone: "",
      address: "",
    });
    expect(readProfile(["staff@brasaland.com"])).toEqual({
      email: "",
      name: "",
      phone: "",
      address: "",
    });
  });
});

describe("nameFieldError", () => {
  test("accepts a name that contains non-space characters", () => {
    expect(nameFieldError(" Camila ")).toBe("");
  });

  test("rejects a blank name", () => {
    expect(nameFieldError("   ")).toBe(NAME_ERROR);
  });
});

describe("phoneFieldError", () => {
  test("accepts a phone number that contains non-space characters", () => {
    expect(phoneFieldError(" +57 300 ")).toBe("");
  });

  test("rejects a blank phone number", () => {
    expect(phoneFieldError("")).toBe(PHONE_ERROR);
  });
});

describe("addressFieldError", () => {
  test("accepts an address that contains non-space characters", () => {
    expect(addressFieldError(" Medellin ")).toBe("");
  });

  test("rejects a blank address", () => {
    expect(addressFieldError("  ")).toBe(ADDRESS_ERROR);
  });
});

describe("profileUpdatePayload", () => {
  test("returns the trimmed name, phone, and address", () => {
    expect(
      profileUpdatePayload({
        name: " Camila ",
        phone: " +57 300 ",
        address: " Medellin ",
      }),
    ).toEqual({
      name: "Camila",
      phone: "+57 300",
      address: "Medellin",
    });
  });

  test("returns null when any required field is blank", () => {
    expect(
      profileUpdatePayload({
        name: "Camila",
        phone: "   ",
        address: "Medellin",
      }),
    ).toBeNull();
  });
});

describe("mergeSavedProfile", () => {
  test("keeps the saved profile fields", () => {
    expect(
      mergeSavedProfile(
        {
          email: "staff@brasaland.com",
          name: "Camila",
          phone: "+57 300",
          address: "Medellin",
        },
        { name: "Other", phone: "+1 305", address: "Miami" },
        "old@brasaland.com",
      ),
    ).toEqual({
      email: "staff@brasaland.com",
      name: "Camila",
      phone: "+57 300",
      address: "Medellin",
    });
  });

  test("falls back when the saved profile omits a field", () => {
    expect(
      mergeSavedProfile(
        { email: "", name: "", phone: "", address: "" },
        { name: "Camila", phone: "+57 300", address: "Medellin" },
        "staff@brasaland.com",
      ),
    ).toEqual({
      email: "staff@brasaland.com",
      name: "Camila",
      phone: "+57 300",
      address: "Medellin",
    });
  });
});
