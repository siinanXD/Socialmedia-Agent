import type { CreatorClient } from "../auth/creator";
import type { ProfileValues } from "./validate";

const UNIQUE_VIOLATION = "23505";
const COLUMNS = "niche, platforms, tone, target_audience, hashtags, allowed_sources, publish_enabled";

async function creatorId(client: CreatorClient, userId: string): Promise<string | null> {
  const { data, error } = await client.from("creators").select("id").eq("user_id", userId).maybeSingle();
  if (error) throw new Error("Profil konnte nicht geladen werden");
  return data?.id ?? null;
}

/** Liest das eigene Profil (RLS); `null`, wenn noch keins gespeichert ist. */
export async function loadProfile(client: CreatorClient, userId: string): Promise<ProfileValues | null> {
  const id = await creatorId(client, userId);
  if (!id) return null;
  const { data, error } = await client.from("creator_profiles").select(COLUMNS).eq("creator_id", id).maybeSingle();
  if (error) throw new Error("Profil konnte nicht geladen werden");
  return (data as ProfileValues | null) ?? null;
}

/**
 * Speichert unter RLS des Nutzers: Anlegen oder Ändern, identische Werte ändern nichts (Audit überspringt sie).
 * Kein Upsert: der Nutzer darf creator_id nicht aktualisieren (Spaltenrecht).
 */
export async function saveProfile(client: CreatorClient, userId: string, values: ProfileValues): Promise<void> {
  const id = await creatorId(client, userId);
  if (!id) throw new Error("Profil konnte nicht gespeichert werden");

  const existing = await client.from("creator_profiles").select("creator_id").eq("creator_id", id).maybeSingle();
  if (existing.error) throw new Error("Profil konnte nicht gespeichert werden");

  if (!existing.data) {
    const { error } = await client.from("creator_profiles").insert({ creator_id: id, ...values });
    if (!error) return;
    // Ein paralleler Aufruf war schneller: dann ändern statt anlegen.
    if (error.code !== UNIQUE_VIOLATION) throw new Error("Profil konnte nicht gespeichert werden");
  }
  const { error } = await client.from("creator_profiles").update(values).eq("creator_id", id);
  if (error) throw new Error("Profil konnte nicht gespeichert werden");
}
