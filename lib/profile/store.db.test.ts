// Läuft nur gegen eine echte lokale Supabase (siehe README „Datenbank lokal“):
//   SUPABASE_TEST_URL=http://127.0.0.1:54321 SUPABASE_TEST_ANON_KEY=<anon key aus `supabase status`> npm test
// Ohne diese Werte (z. B. in der CI, die nur `supabase db start` ausführt) wird übersprungen.
import { createClient } from "@supabase/supabase-js";
import { describe, expect, it } from "vitest";
import { ensureCreator, type CreatorClient } from "../auth/creator";
import { loadProfile, saveProfile } from "./store";
import type { ProfileValues } from "./validate";

const url = process.env.SUPABASE_TEST_URL;
const anon = process.env.SUPABASE_TEST_ANON_KEY;

const VALUES: ProfileValues = {
  niche: "Fitness",
  tone: "locker",
  target_audience: "Einsteiger",
  platforms: ["youtube", "tiktok"],
  allowed_sources: ["creator_submitted"],
  hashtags: ["#fitness", "#gym"],
  publish_enabled: false,
};

async function newUser(): Promise<{ client: CreatorClient; userId: string }> {
  const client = createClient(url!, anon!, { db: { schema: "social_media" }, auth: { persistSession: false } }) as unknown as CreatorClient;
  const email = `profil-${crypto.randomUUID()}@example.test`;
  const { data, error } = await client.auth.signUp({ email, password: "test-passwort-1234" });
  if (error || !data.user || !data.session) throw new Error("Testnutzer konnte nicht angelegt werden (E-Mail-Bestätigung an?)");
  await ensureCreator(client, data.user.id);
  return { client, userId: data.user.id };
}

describe.skipIf(!url || !anon)("Profil speichern (lokale Supabase, RLS des Nutzers)", () => {
  it("ohne gespeichertes Profil ist nichts da", async () => {
    const a = await newUser();
    expect(await loadProfile(a.client, a.userId)).toBeNull();
  });

  it("speichert und lädt das Profil; Veröffentlichen steht ohne Häkchen auf aus", async () => {
    const a = await newUser();
    expect(await saveProfile(a.client, a.userId, VALUES)).toBe(true);
    const p = await loadProfile(a.client, a.userId);
    expect(p).toMatchObject({ ...VALUES, publish_enabled: false });
  });

  it("zweimal dasselbe speichern ergibt eine Zeile und nur einen Audit-Eintrag", async () => {
    const a = await newUser();
    await saveProfile(a.client, a.userId, VALUES);
    await saveProfile(a.client, a.userId, VALUES);
    const profiles = await a.client.from("creator_profiles").select("creator_id");
    const audit = await a.client.from("profile_audit").select("action");
    expect(profiles.data).toHaveLength(1);
    expect(audit.data).toEqual([{ action: "insert" }]);
  });

  it("eine Änderung landet im Audit; Einschalten und Ausschalten des Schalters ebenfalls", async () => {
    const a = await newUser();
    await saveProfile(a.client, a.userId, VALUES);
    await saveProfile(a.client, a.userId, { ...VALUES, publish_enabled: true });
    expect((await loadProfile(a.client, a.userId))?.publish_enabled).toBe(true);
    await saveProfile(a.client, a.userId, { ...VALUES, publish_enabled: false });
    const audit = await a.client.from("profile_audit").select("action, new_values").order("id");
    expect(audit.data?.map((r) => r.action)).toEqual(["insert", "update", "update"]);
    expect(audit.data?.map((r) => r.new_values.publish_enabled)).toEqual([false, true, false]);
  });

  it("ein zweiter Nutzer sieht das Profil des ersten nicht und ändert es nicht", async () => {
    const a = await newUser();
    const b = await newUser();
    await saveProfile(a.client, a.userId, VALUES);
    expect(await loadProfile(b.client, b.userId)).toBeNull();
    expect((await b.client.from("creator_profiles").select("creator_id")).data).toEqual([]);
    expect((await b.client.from("profile_audit").select("id")).data).toEqual([]);
    // b speichert sein eigenes Profil; das von a bleibt unverändert.
    await saveProfile(b.client, b.userId, { ...VALUES, niche: "Kochen" });
    expect((await loadProfile(a.client, a.userId))?.niche).toBe("Fitness");
    expect((await loadProfile(b.client, b.userId))?.niche).toBe("Kochen");
  });

  it("die Datenbank lehnt ungültige Werte auch ohne die App-Prüfung ab; saveProfile meldet false", async () => {
    const a = await newUser();
    expect(await saveProfile(a.client, a.userId, { ...VALUES, platforms: ["myspace"] })).toBe(false);
    expect(await saveProfile(a.client, a.userId, { ...VALUES, allowed_sources: ["scraping"] })).toBe(false);
    const tooMany = Array.from({ length: 31 }, (_, i) => `#t${i}`);
    expect(await saveProfile(a.client, a.userId, { ...VALUES, hashtags: tooMany })).toBe(false);
    expect(await loadProfile(a.client, a.userId)).toBeNull();
  });
});
