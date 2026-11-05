import { describe, expect, it } from "vitest";
import { parseProfileForm } from "./validate";

function form(entries: [string, string][]): FormData {
  const fd = new FormData();
  for (const [k, v] of entries) fd.append(k, v);
  return fd;
}

const BASIS: [string, string][] = [
  ["niche", "Fitness"],
  ["tone", "locker, direkt"],
  ["target_audience", "Einsteiger zwischen 18 und 30"],
];

describe("parseProfileForm", () => {
  it("nimmt ein gültiges Profil an; Veröffentlichen ist ohne Häkchen aus", () => {
    const r = parseProfileForm(form([...BASIS, ["platforms", "youtube"], ["platforms", "tiktok"], ["allowed_sources", "creator_submitted"]]));
    expect(r).toEqual({
      ok: true,
      values: {
        niche: "Fitness",
        tone: "locker, direkt",
        target_audience: "Einsteiger zwischen 18 und 30",
        platforms: ["youtube", "tiktok"],
        allowed_sources: ["creator_submitted"],
        hashtags: [],
        publish_enabled: false,
      },
    });
  });

  it("leeres Formular ergibt restriktive Standardwerte", () => {
    const r = parseProfileForm(form([]));
    expect(r).toMatchObject({ ok: true, values: { niche: "", platforms: [], allowed_sources: [], hashtags: [], publish_enabled: false } });
  });

  it("lehnt eine unbekannte Plattform ab", () => {
    expect(parseProfileForm(form([["platforms", "myspace"]]))).toEqual({ ok: false, code: "plattform" });
  });

  it("lehnt eine nicht erlaubte Quelle ab", () => {
    expect(parseProfileForm(form([["allowed_sources", "scraping"]]))).toEqual({ ok: false, code: "quelle" });
  });

  it("lehnt zu lange Texte ab", () => {
    expect(parseProfileForm(form([["niche", "x".repeat(101)]]))).toEqual({ ok: false, code: "nische" });
    expect(parseProfileForm(form([["tone", "x".repeat(501)]]))).toEqual({ ok: false, code: "tonalitaet" });
    expect(parseProfileForm(form([["target_audience", "x".repeat(501)]]))).toEqual({ ok: false, code: "zielgruppe" });
  });

  it("Veröffentlichen wird nur mit ausdrücklichem Häkchen an", () => {
    expect(parseProfileForm(form([["publish_enabled", "on"]]))).toMatchObject({ ok: true, values: { publish_enabled: true } });
    expect(parseProfileForm(form([["publish_enabled", "true"]]))).toMatchObject({ ok: true, values: { publish_enabled: false } });
  });

  describe("Hashtags", () => {
    it("normalisiert auf genau ein führendes # und entfernt Doppelte", () => {
      const r = parseProfileForm(form([["hashtags", "fitness, #Fitness ##gym\nworkout   #gym"]]));
      expect(r).toMatchObject({ ok: true, values: { hashtags: ["#fitness", "#gym", "#workout"] } });
    });

    it("erlaubt höchstens 30", () => {
      const dreissig = Array.from({ length: 30 }, (_, i) => `t${i}`).join(" ");
      expect(parseProfileForm(form([["hashtags", dreissig]]))).toMatchObject({ ok: true });
      expect(parseProfileForm(form([["hashtags", dreissig + " t30"]]))).toEqual({ ok: false, code: "hashtags_anzahl" });
    });

    it("lehnt Zeichen ab, die in Hashtags nicht vorkommen", () => {
      expect(parseProfileForm(form([["hashtags", "#gut #sch<ön>"]]))).toEqual({ ok: false, code: "hashtags_zeichen" });
      expect(parseProfileForm(form([["hashtags", "#"]]))).toEqual({ ok: false, code: "hashtags_zeichen" });
    });

    it("lehnt einen zu langen Hashtag ab", () => {
      expect(parseProfileForm(form([["hashtags", "a".repeat(51)]]))).toEqual({ ok: false, code: "hashtags_zeichen" });
    });
  });
});
