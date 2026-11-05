import { describe, expect, it } from "vitest";
import { SECTIONS } from "../lib/studio/sections";

describe("Leerzustand der Mediathek (Ziel nach der Anmeldung)", () => {
  it("nennt den nächsten Schritt und sagt ehrlich, dass der Upload noch fehlt", () => {
    const m = SECTIONS.find((s) => s.href === "/mediathek");
    expect(m?.leer.titel).toBe("Noch keine Medien");
    expect(m?.leer.text).toMatch(/Als Nächstes/);
    expect(m?.leer.text).toMatch(/Upload/);
    expect(m?.leer.text).toMatch(/noch nichts zu tun/);
  });
});
