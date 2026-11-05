// Allowlists und Grenzen spiegeln die CHECKs in supabase/migrations/*_sin1382_creator_profiles.sql.
export const PLATFORMS = [
  { value: "youtube", label: "YouTube Shorts" },
  { value: "instagram", label: "Instagram Reels" },
  { value: "tiktok", label: "TikTok" },
] as const;

export const SOURCES = [
  { value: "creator_submitted", label: "Vom Creator hochgeladen" },
  { value: "official_api", label: "Offizielle Plattform-Schnittstelle" },
  { value: "manual_import", label: "Manueller Import" },
] as const;

export const MAX_NICHE = 100;
export const MAX_TEXT = 500;
export const MAX_HASHTAGS = 30;
const MAX_HASHTAG_LENGTH = 50;

export type ProfileValues = {
  niche: string;
  platforms: string[];
  tone: string;
  target_audience: string;
  hashtags: string[];
  allowed_sources: string[];
  publish_enabled: boolean;
};

export type FieldErrors = Partial<Record<"niche" | "platform" | "tone" | "target_audience" | "hashtags" | "source", string>>;

export type ParseResult = { ok: true; values: ProfileValues } | { ok: false; errors: FieldErrors };

/** Trennt an Leerraum/Komma, setzt genau ein führendes `#`, entfernt Doppelte (Reihenfolge bleibt). */
export function normalizeHashtags(raw: string): { ok: true; tags: string[] } | { ok: false; error: string } {
  const tags: string[] = [];
  for (const part of raw.split(/[\s,]+/)) {
    const word = part.replace(/^#+/, "");
    if (!word) continue;
    if (!/^[\p{L}\p{N}_]+$/u.test(word) || word.length > MAX_HASHTAG_LENGTH) {
      return { ok: false, error: "Hashtags dürfen nur Buchstaben, Ziffern und Unterstrich enthalten (höchstens 50 Zeichen)." };
    }
    const tag = "#" + word;
    if (!tags.includes(tag)) tags.push(tag);
  }
  if (tags.length > MAX_HASHTAGS) return { ok: false, error: `Höchstens ${MAX_HASHTAGS} Hashtags.` };
  return { ok: true, tags };
}

function text(formData: FormData, name: string): string {
  const v = formData.get(name);
  return typeof v === "string" ? v.trim() : "";
}

function picked(formData: FormData, name: string, allowed: readonly { value: string }[]): string[] | null {
  const values = formData.getAll(name).filter((v): v is string => typeof v === "string");
  if (values.some((v) => !allowed.some((a) => a.value === v))) return null;
  return [...new Set(values)];
}

export function parseProfileForm(formData: FormData): ParseResult {
  const errors: FieldErrors = {};
  const niche = text(formData, "niche");
  const tone = text(formData, "tone");
  const target_audience = text(formData, "target_audience");
  if (niche.length > MAX_NICHE) errors.niche = `Höchstens ${MAX_NICHE} Zeichen.`;
  if (tone.length > MAX_TEXT) errors.tone = `Höchstens ${MAX_TEXT} Zeichen.`;
  if (target_audience.length > MAX_TEXT) errors.target_audience = `Höchstens ${MAX_TEXT} Zeichen.`;

  const platforms = picked(formData, "platform", PLATFORMS);
  if (!platforms) errors.platform = "Bitte nur Plattformen aus der Liste wählen.";
  const allowed_sources = picked(formData, "source", SOURCES);
  if (!allowed_sources) errors.source = "Bitte nur Quellen aus der Liste wählen.";

  const tags = normalizeHashtags(text(formData, "hashtags"));
  if (!tags.ok) errors.hashtags = tags.error;

  if (Object.keys(errors).length > 0 || !platforms || !allowed_sources || !tags.ok) return { ok: false, errors };
  return {
    ok: true,
    values: {
      niche, platforms, tone, target_audience,
      hashtags: tags.tags, allowed_sources,
      // Nur ein ausdrückliches Häkchen schaltet ein; fehlt das Feld, bleibt es aus.
      publish_enabled: formData.get("publish_enabled") === "on",
    },
  };
}
