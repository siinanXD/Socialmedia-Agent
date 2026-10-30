import type { SupabaseClient } from "@supabase/supabase-js";

export type CreatorClient = SupabaseClient<any, "social_media", "social_media">; // eslint-disable-line @typescript-eslint/no-explicit-any

const UNIQUE_VIOLATION = "23505";

/**
 * Stellt sicher, dass es zu diesem Login genau eine Zeile in social_media.creators gibt.
 * Läuft unter RLS (Policy creators_insert_own); idempotent, auch bei parallelen Aufrufen.
 */
export async function ensureCreator(client: CreatorClient, userId: string): Promise<void> {
  const existing = await client.from("creators").select("id").eq("user_id", userId).maybeSingle();
  if (existing.error) throw new Error("Creator konnte nicht angelegt werden");
  if (existing.data) return;

  const { error } = await client.from("creators").insert({ user_id: userId });
  // Ein paralleler Aufruf war schneller: Zeile existiert, das Ziel ist erreicht.
  if (error && error.code !== UNIQUE_VIOLATION) throw new Error("Creator konnte nicht angelegt werden");
}
