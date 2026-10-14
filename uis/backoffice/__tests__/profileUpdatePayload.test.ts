import { profileUpdatePayload } from "../lib/profile";

describe("profileUpdatePayload (FE-019)", () => {
  test("returns trimmed name, phone, and address", () => {
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

  test("returns null when a required field is blank", () => {
    expect(
      profileUpdatePayload({
        name: "",
        phone: "+57 300",
        address: "Medellin",
      }),
    ).toBeNull();
  });
});
