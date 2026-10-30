import { describe, expect, it } from "vitest";
import { messageFor } from "./messages";

describe("messageFor", () => {
  it("kennt feste Codes", () => {
    expect(messageFor("anmeldung")).toMatch(/E-Mail und Passwort/);
  });
  it("gibt für unbekannte Codes (z. B. manipulierte URL) nichts aus", () => {
    expect(messageFor("<script>alert(1)</script>")).toBeNull();
    expect(messageFor(undefined)).toBeNull();
  });
});
