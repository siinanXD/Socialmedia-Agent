import { describe, expect, it } from "vitest";
import type { CreatorClient } from "../auth/creator";
import { loadProfile, saveProfile } from "./save";
import type { ProfileValues } from "./validate";

const values: ProfileValues = {
  niche: "Fitness", platforms: ["youtube"], tone: "motivierend", target_audience: "Einsteiger",
  hashtags: ["#gym"], allowed_sources: [], publish_enabled: false,
};

/** In-Memory-Ersatz: creators (user_id -> id) und creator_profiles (creator_id eindeutig, Fehler 23505). */
function fakeClient(opts: { updateError?: boolean } = {}) {
  const creators = [{ id: "c1", user_id: "u1" }, { id: "c2", user_id: "u2" }];
  const profiles: Record<string, unknown>[] = [];
  const client = {
    from: (table: string) => {
      if (table === "creators") {
        return { select: () => ({ eq: (_c: string, uid: string) => ({
          maybeSingle: async () => ({ data: creators.find((c) => c.user_id === uid) ?? null, error: null }) }) }) };
      }
      return {
        select: () => ({ eq: (_c: string, id: string) => ({
          maybeSingle: async () => ({ data: profiles.find((p) => p.creator_id === id) ?? null, error: null }) }) }),
        insert: async (row: Record<string, unknown>) => {
          if (profiles.some((p) => p.creator_id === row.creator_id)) return { error: { code: "23505" } };
          profiles.push({ ...row });
          return { error: null };
        },
        update: (row: Record<string, unknown>) => ({ eq: async (_c: string, id: string) => {
          if (opts.updateError) return { error: { code: "42501", message: "interne Details" } };
          const p = profiles.find((x) => x.creator_id === id);
          if (p) Object.assign(p, row);
          return { error: null };
        } }),
      };
    },
  };
  return { client: client as unknown as CreatorClient, profiles };
}

describe("saveProfile", () => {
  it("legt das Profil beim ersten Speichern an", async () => {
    const { client, profiles } = fakeClient();
    await saveProfile(client, "u1", values);
    expect(profiles).toHaveLength(1);
    expect(profiles[0]).toMatchObject({ creator_id: "c1", niche: "Fitness", publish_enabled: false });
  });
  it("ist idempotent: zweimal speichern ergibt genau eine Zeile mit gleichem Inhalt", async () => {
    const { client, profiles } = fakeClient();
    await saveProfile(client, "u1", values);
    const first = JSON.stringify(profiles);
    await saveProfile(client, "u1", values);
    expect(profiles).toHaveLength(1);
    expect(JSON.stringify(profiles)).toBe(first);
  });
  it("trennt Nutzer: u2 sieht das Profil von u1 nicht", async () => {
    const { client } = fakeClient();
    await saveProfile(client, "u1", values);
    expect(await loadProfile(client, "u2")).toBeNull();
    expect((await loadProfile(client, "u1"))?.niche).toBe("Fitness");
  });
  it("wirft bei Datenbankfehler ohne Details der Rohmeldung", async () => {
    const { client } = fakeClient({ updateError: true });
    await saveProfile(client, "u1", values);
    await expect(saveProfile(client, "u1", values)).rejects.toThrow(/^Profil konnte nicht gespeichert werden$/);
  });
});
