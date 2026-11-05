import { describe, expect, it } from "vitest";
import { parseProfileForm, normalizeHashtags } from "./validate";

function form(entries: [string, string][]): FormData {
  const f = new FormData();
  for (const [k, v] of entries) f.append(k, v);
  return f;
}

describe("normalizeHashtags", () => {
  it("setzt # davor, trennt an Leerraum/Komma und entfernt Doppelte", () => {
    expect(normalizeHashtags("fitness, #Gym  ##gym\nfitness")).toEqual({ ok: true, tags: ["#fitness", "#Gym", "#gym"] });
  });
  it("lehnt mehr als 30 Hashtags ab", () => {
    const many = Array.from({ length: 31 }, (_, i) => `t${i}`).join(" ");
    expect(normalizeHashtags(many).ok).toBe(false);
  });
  it("lehnt Sonderzeichen ab", () => {
    expect(normalizeHashtags("ok <script>").ok).toBe(false);
  });
});

describe("parseProfileForm", () => {
  it("übernimmt gültige Werte; Veröffentlichen ist ohne Häkchen aus", () => {
    const r = parseProfileForm(
      form([["niche", " Fitness "], ["platform", "youtube"], ["platform", "tiktok"], ["source", "manual_import"], ["hashtags", "gym"]]),
    );
    expect(r).toEqual({
      ok: true,
      values: {
        niche: "Fitness", platforms: ["youtube", "tiktok"], tone: "", target_audience: "",
        hashtags: ["#gym"], allowed_sources: ["manual_import"], publish_enabled: false,
      },
    });
  });
  it("lehnt unbekannte Plattform ab", () => {
    expect(parseProfileForm(form([["platform", "myspace"]])).ok).toBe(false);
  });
  it("lehnt unbekannte Quelle ab", () => {
    expect(parseProfileForm(form([["source", "scraping"]])).ok).toBe(false);
  });
  it("lehnt zu lange Texte ab", () => {
    expect(parseProfileForm(form([["niche", "x".repeat(101)]])).ok).toBe(false);
    expect(parseProfileForm(form([["tone", "x".repeat(501)]])).ok).toBe(false);
    expect(parseProfileForm(form([["target_audience", "x".repeat(501)]])).ok).toBe(false);
  });
  it("lehnt zu viele Hashtags ab", () => {
    const many = Array.from({ length: 31 }, (_, i) => `t${i}`).join(" ");
    expect(parseProfileForm(form([["hashtags", many]])).ok).toBe(false);
  });
  it("Veröffentlichen nur bei ausdrücklichem Häkchen an", () => {
    const r = parseProfileForm(form([["publish_enabled", "on"]]));
    expect(r.ok && r.values.publish_enabled).toBe(true);
  });
});
