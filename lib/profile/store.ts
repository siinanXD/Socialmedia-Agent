import type { CreatorClient } from "../auth/creator";
import type { ProfileValues } from "./validate";

const COLUMNS = "niche, tone, target_audience, platforms, allowed_sources, hashtags, publish_enabled";
const UNIQUE_VIOLATION = "23505";

async function creatorId(client: CreatorClient, userId: string): Promise<string | null> {
  const { data, error } = await client.from("creators").select("id").eq("user_id", userId).maybeSingle();
  if (error) throw new Error("Creator konnte nicht gelesen werden");
  return data?.id ?? null;
}

/** Das eigene Profil (RLS: nur der eigene Creator ist sichtbar) oder null, wenn noch keins gespeichert wurde. */
export async function loadProfile(client: CreatorClient, userId: string): Promise<ProfileValues | null> {
  const id = await creatorId(client, userId);
  if (!id) return null;
  const { data, error } = await client.from("creator_profiles").select(COLUMNS).eq("creator_id", id).maybeSingle();
  if (error) throw new Error("Profil konnte nicht gelesen werden");
  return (data as ProfileValues | null) ?? null;
}

/**
 * Speichert unter den Rechten des Nutzers. Idempotent: gleiche Werte ändern nichts (der Audit-Trigger
 * überspringt unveränderte Zeilen). Gibt false zurück, wenn die Datenbank ablehnt; Details bleiben intern.
 * Nur die hier gelisteten Spalten werden geschrieben; Budget, Referenzaccounts und KPIs bleiben unberührt.
 */
export async function saveProfile(client: CreatorClient, userId: string, values: ProfileValues): Promise<boolean> {
  const id = await creatorId(client, userId);
  if (!id) return false;

  // Kein upsert: PostgREST würde creator_id mitschreiben, und dafür hat der Nutzer kein UPDATE-Recht.
  const update = () => client.from("creator_profiles").update(values).eq("creator_id", id).select("creator_id");
  const first = await update();
  if (first.error) return false;
  if (first.data.length > 0) return true;

  const { error } = await client.from("creator_profiles").insert({ creator_id: id, ...values });
  if (!error) return true;
  // Ein paralleler Aufruf war schneller: dann aktualisieren statt doppelt anlegen.
  if (error.code !== UNIQUE_VIOLATION) return false;
  const retry = await update();
  return !retry.error && retry.data.length > 0;
}
