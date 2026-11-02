import { describe, expect, it } from "vitest";
import { zugangAus } from "./zugang";

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
