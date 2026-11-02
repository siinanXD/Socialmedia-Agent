import { describe, expect, it } from "vitest";
import { isActive, SECTIONS } from "./sections";

describe("isActive", () => {
  it("markiert die Route und ihre Unterseiten", () => {
    expect(isActive("/mediathek", "/mediathek")).toBe(true);
    expect(isActive("/mediathek/abc", "/mediathek")).toBe(true);
  });
  it("markiert keine fremde oder ähnlich beginnende Route", () => {
    expect(isActive("/highlights", "/mediathek")).toBe(false);
    expect(isActive("/mediathek-neu", "/mediathek")).toBe(false);
  });
  it("kennt die vier Bereiche", () => {
    expect(SECTIONS.map((s) => s.href)).toEqual(["/mediathek", "/highlights", "/auftraege", "/freigabe"]);
  });
});
