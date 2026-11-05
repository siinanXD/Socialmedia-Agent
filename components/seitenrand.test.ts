import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const css = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");
const MOBILE = css.slice(css.indexOf("@media (max-width: 40rem)"));
const DESKTOP = css.slice(0, css.indexOf("@media (max-width: 40rem)"));

// Mehrere Regeln können denselben Selektor haben (z. B. die gemeinsame min-width-Regel); die mit padding zählt.
const rule = (block: string, selector: string) =>
  [...block.matchAll(new RegExp(String.raw`(?:^|\n)\s*${selector.replace(".", String.raw`\.`)}\s*\{([^}]*)\}`, "g"))]
    .map((m) => m[1])
    .find((body) => body.includes("padding:")) ?? "";

/** Seitenrand in px links/rechts aus `padding`; 1rem = 16px, --space-N laut :root. */
function sidePx(decl: string): number {
  const tokens: Record<string, number> = { "--space-1": 8, "--space-2": 16, "--space-3": 24, "--space-4": 32 };
  const m = /padding:\s*([^;]+);/.exec(decl)?.[1].trim().split(/\s+/) ?? [];
  const side = m.length === 1 ? m[0] : m[1];
  const v = /var\((--space-\d)\)/.exec(side ?? "");
  if (v) return tokens[v[1]];
  const rem = /^([\d.]+)rem$/.exec(side ?? "");
  return rem ? Number(rem[1]) * 16 : 0;
}

describe("Seitenrand mindestens 16 px (Klickprobe SIN-1487, Regel „rand“)", () => {
  it("Anmeldeseiten haben auf Desktop und Handy 16 px links und rechts", () => {
    expect(sidePx(rule(DESKTOP, ".auth"))).toBeGreaterThanOrEqual(16);
    expect(MOBILE).not.toMatch(/\.auth\s*\{[^}]*padding:\s*0/);
  });
  it("Shell (Ziel von /) hat auf Desktop und Handy mindestens 16 px", () => {
    expect(sidePx(rule(DESKTOP, ".content"))).toBeGreaterThanOrEqual(16);
    expect(sidePx(rule(MOBILE, ".content"))).toBeGreaterThanOrEqual(16);
    expect(sidePx(rule(MOBILE, ".topbar"))).toBeGreaterThanOrEqual(16);
    expect(sidePx(rule(MOBILE, ".sidebar"))).toBeGreaterThanOrEqual(16);
  });
});
