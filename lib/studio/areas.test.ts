import { describe, expect, it } from "vitest";
import { AREAS, isActive } from "./areas";

describe("AREAS", () => {
  it("hat die vier Bereiche in Figma-Reihenfolge", () => {
    expect(AREAS.map((a) => a.href)).toEqual(["/mediathek", "/highlights", "/auftraege", "/freigabe"]);
    expect(AREAS.map((a) => a.nr)).toEqual(["01", "02", "03", "04"]);
  });
});

describe("isActive", () => {
  it("markiert die Route selbst und Unterseiten", () => {
    expect(isActive("/mediathek", "/mediathek")).toBe(true);
    expect(isActive("/mediathek/abc", "/mediathek")).toBe(true);
  });
  it("markiert andere Routen und Präfix-Treffer nicht", () => {
    expect(isActive("/highlights", "/mediathek")).toBe(false);
    expect(isActive("/mediathek-alt", "/mediathek")).toBe(false);
    expect(isActive("/", "/mediathek")).toBe(false);
  });
});
