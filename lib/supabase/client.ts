import { createBrowserClient } from "@supabase/ssr";
import { supabaseEnv } from "./env";

/** Supabase-Client für den Browser. Nur anon-Schlüssel, Zugriff immer über RLS. */
export function createClient() {
  const { url, anonKey } = supabaseEnv();
  return createBrowserClient(url, anonKey, { db: { schema: "social_media" } });
}
