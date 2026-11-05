import { describe, expect, it } from "vitest";
import { isActive, SECTIONS } from "./sections";

describe("isActive", () => {
  it("markiert die aktuelle Route und Unterrouten", () => {
    expect(isActive("/mediathek", "/mediathek")).toBe(true);
    expect(isActive("/mediathek/abc", "/mediathek")).toBe(true);
  });
  it("markiert keine andere Route", () => {
    expect(isActive("/highlights", "/mediathek")).toBe(false);
    expect(isActive("/mediathek-x", "/mediathek")).toBe(false);
  });
  it("hat fünf Bereiche", () => {
    expect(SECTIONS.map((s) => s.href)).toEqual(["/mediathek", "/highlights", "/auftraege", "/freigabe", "/profil"]);
  });
});
