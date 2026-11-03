import { describe, expect, it } from "vitest";
import { NAV_ITEMS, creatorLabel, isActiveRoute } from "./nav";

describe("NAV_ITEMS", () => {
  it("hat die vier Bereiche in fester Reihenfolge", () => {
    expect(NAV_ITEMS.map((i) => i.href)).toEqual(["/mediathek", "/highlights", "/auftraege", "/freigabe"]);
    expect(NAV_ITEMS.map((i) => i.number)).toEqual(["01", "02", "03", "04"]);
  });
});

describe("isActiveRoute", () => {
  it("markiert die exakte Route", () => {
    expect(isActiveRoute("/mediathek", "/mediathek")).toBe(true);
  });
  it("markiert Unterrouten", () => {
    expect(isActiveRoute("/auftraege/123", "/auftraege")).toBe(true);
  });
  it("markiert keine anderen Bereiche oder Präfix-Treffer", () => {
    expect(isActiveRoute("/highlights", "/mediathek")).toBe(false);
    expect(isActiveRoute("/mediathekx", "/mediathek")).toBe(false);
  });
});

describe("creatorLabel", () => {
  it("bevorzugt den Anzeigenamen", () => {
    expect(creatorLabel("Mia", "mia@example.com")).toBe("Mia");
  });
  it("fällt auf die E-Mail zurück", () => {
    expect(creatorLabel("  ", "mia@example.com")).toBe("mia@example.com");
    expect(creatorLabel(null, "mia@example.com")).toBe("mia@example.com");
  });
});
