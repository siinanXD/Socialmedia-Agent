// Allowlists und Grenzen spiegeln die CHECKs in supabase/migrations/20261105010000_sin1382_creator_profiles.sql.
export const PLATFORMS = [
  { value: "youtube", label: "YouTube" },
  { value: "instagram", label: "Instagram" },
  { value: "tiktok", label: "TikTok" },
] as const;

export const SOURCES = [
  { value: "creator_submitted", label: "Von mir selbst eingereicht" },
  { value: "official_api", label: "Offizielle Plattform-Schnittstelle" },
  { value: "manual_import", label: "Manueller Import" },
] as const;

export const MAX_NICHE = 100;
export const MAX_TEXT = 500;
export const MAX_HASHTAGS = 30;
const MAX_HASHTAG_LENGTH = 50;
const MAX_HASHTAGS_TOTAL = 1500;

export type ProfileValues = {
  niche: string;
  tone: string;
  target_audience: string;
  platforms: string[];
  allowed_sources: string[];
  hashtags: string[];
  publish_enabled: boolean;
};

export type ProfileErrorCode =
  | "nische"
  | "tonalitaet"
  | "zielgruppe"
  | "plattform"
  | "quelle"
  | "hashtags_anzahl"
  | "hashtags_zeichen";

export type ParseResult = { ok: true; values: ProfileValues } | { ok: false; code: ProfileErrorCode };

function text(fd: FormData, name: string): string {
  const v = fd.get(name);
  return typeof v === "string" ? v.trim() : "";
}

function pick(fd: FormData, name: string, allowed: readonly { value: string }[]): string[] | null {
  const values = fd.getAll(name).filter((v): v is string => typeof v === "string");
  const ok = new Set(allowed.map((a) => a.value));
  if (values.some((v) => !ok.has(v))) return null;
  return [...new Set(values)];
}

// Unicode-Buchstaben und -Ziffern sowie Unterstrich, wie sie Plattformen in Hashtags zulassen.
const HASHTAG_BODY = /^[\p{L}\p{N}_]+$/u;

function hashtags(raw: string): string[] | "zeichen" | "anzahl" {
  const parts = raw.split(/[\s,]+/).filter(Boolean);
  const tags: string[] = [];
  for (const part of parts) {
    const body = part.replace(/^#+/, "").toLowerCase();
    if (!body || body.length > MAX_HASHTAG_LENGTH || !HASHTAG_BODY.test(body)) return "zeichen";
    const tag = `#${body}`;
    if (!tags.includes(tag)) tags.push(tag);
  }
  if (tags.length > MAX_HASHTAGS || tags.join(" ").length > MAX_HASHTAGS_TOTAL) return "anzahl";
  return tags;
}

/** Prüft das Profilformular serverseitig; die Datenbank-CHECKs sind die zweite Schranke. */
export function parseProfileForm(fd: FormData): ParseResult {
  const niche = text(fd, "niche");
  const tone = text(fd, "tone");
  const target_audience = text(fd, "target_audience");
  if (niche.length > MAX_NICHE) return { ok: false, code: "nische" };
  if (tone.length > MAX_TEXT) return { ok: false, code: "tonalitaet" };
  if (target_audience.length > MAX_TEXT) return { ok: false, code: "zielgruppe" };

  const platforms = pick(fd, "platforms", PLATFORMS);
  if (!platforms) return { ok: false, code: "plattform" };
  const allowed_sources = pick(fd, "allowed_sources", SOURCES);
  if (!allowed_sources) return { ok: false, code: "quelle" };

  const tags = hashtags(text(fd, "hashtags"));
  if (tags === "zeichen") return { ok: false, code: "hashtags_zeichen" };
  if (tags === "anzahl") return { ok: false, code: "hashtags_anzahl" };

  // Nur das ausdrückliche Häkchen schaltet ein; alles andere bleibt aus.
  const publish_enabled = fd.get("publish_enabled") === "on";
  return { ok: true, values: { niche, tone, target_audience, platforms, allowed_sources, hashtags: tags, publish_enabled } };
}
