import { describe, expect, it } from "vitest";
import { SECTIONS } from "../lib/studio/sections";

describe("Leerzustand der Mediathek (Ziel nach der Anmeldung)", () => {
  it("nennt den nächsten Schritt: hochladen, nur für dich sichtbar", () => {
    const m = SECTIONS.find((s) => s.href === "/mediathek");
    expect(m?.leer.titel).toBe("Noch keine Medien");
    expect(m?.leer.text).toMatch(/hoch/);
    expect(m?.leer.text).toMatch(/nur für dich sichtbar/);
  });
});
