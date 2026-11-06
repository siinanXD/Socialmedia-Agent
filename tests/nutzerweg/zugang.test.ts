import { describe, expect, it } from "vitest";
import { zweitesKontoAus, zugangAus } from "./zugang";

describe("zugangAus", () => {
  it("nennt fehlende Namen, aber keine Werte", () => {
    expect(() => zugangAus({ LIVE_URL: "https://x.test", TESTNUTZER_PASSWORT: "geheim" })).toThrow(
      "Fehlende Umgebungsvariablen: TESTNUTZER_EMAIL",
    );
  });

  it("liefert den Zugang, wenn alles gesetzt ist", () => {
    expect(zugangAus({ LIVE_URL: "https://x.test", TESTNUTZER_EMAIL: "a@b.c", TESTNUTZER_PASSWORT: "pw" })).toEqual({
      liveUrl: "https://x.test",
      email: "a@b.c",
      passwort: "pw",
    });
  });
});

describe("zweitesKontoAus", () => {
  it("nimmt das zweite Testkonto, die Adresse ist überschreibbar", () => {
    expect(zweitesKontoAus({ TESTNUTZER2_PASSWORT: "pw2" })).toEqual({ email: "sinan-test-2@sjcode.de", passwort: "pw2" });
    expect(zweitesKontoAus({ TESTNUTZER2_EMAIL: "b@x.test", TESTNUTZER2_PASSWORT: "pw2" }).email).toBe("b@x.test");
  });

  it("nennt das fehlende Passwort nur beim Namen", () => {
    expect(() => zweitesKontoAus({})).toThrow("Fehlende Umgebungsvariablen: TESTNUTZER2_PASSWORT");
  });
});
