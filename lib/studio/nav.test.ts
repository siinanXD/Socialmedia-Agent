import { describe, expect, it } from "vitest";
import { NAV_ITEMS, isActive } from "./nav";

describe("NAV_ITEMS", () => {
  it("hat die vier Bereiche in Reihenfolge mit deutschen Beschriftungen", () => {
    expect(NAV_ITEMS.map((i) => [i.href, i.label])).toEqual([
      ["/mediathek", "Mediathek"],
      ["/highlights", "Szenen und Highlights"],
      ["/auftraege", "Aufträge"],
      ["/freigabe", "Freigabe und Export"],
    ]);
  });
});

describe("isActive", () => {
  it("markiert die aktuelle Route", () => {
    expect(isActive("/auftraege", "/auftraege")).toBe(true);
  });
  it("markiert Unterseiten", () => {
    expect(isActive("/auftraege/42", "/auftraege")).toBe(true);
  });
  it("markiert andere Routen nicht", () => {
    expect(isActive("/mediathek", "/auftraege")).toBe(false);
  });
  it("verwechselt Präfixe nicht", () => {
    expect(isActive("/auftraege-alt", "/auftraege")).toBe(false);
  });
});
