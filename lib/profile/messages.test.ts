import { describe, expect, it } from "vitest";
import { profileMessage } from "./messages";

describe("profileMessage", () => {
  it("kennt Erfolg und feste Fehlercodes", () => {
    expect(profileMessage({ hinweis: "gespeichert" })).toEqual({ kind: "ok", text: expect.stringContaining("gespeichert") });
    expect(profileMessage({ fehler: "plattform" })).toEqual({ kind: "error", text: expect.stringContaining("Plattform") });
  });

  it("zeigt unbekannte Codes aus der URL nicht an", () => {
    expect(profileMessage({ fehler: "<script>alert(1)</script>" })).toBeNull();
    expect(profileMessage({ hinweis: "x", fehler: undefined })).toBeNull();
    expect(profileMessage({})).toBeNull();
  });

  it("die Fehler zum Speichern und Laden nennen keine internen Details", () => {
    for (const code of ["speichern", "laden"]) {
      const m = profileMessage({ fehler: code });
      expect(m?.kind).toBe("error");
      expect(m?.text).not.toMatch(/postgres|sql|rls|policy|42501|permission|relation|table/i);
    }
  });
});
