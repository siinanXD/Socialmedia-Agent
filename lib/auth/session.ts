import type { SupabaseClient, User } from "@supabase/supabase-js";
import { redirect } from "next/navigation";

/**
 * Serverseitige Anmeldeprüfung beim Auth-Server (zusätzlich zu proxy.ts).
 * Ohne gültige Anmeldung geht es auf /login.
 */
export async function requireUser(client: Pick<SupabaseClient, "auth">): Promise<User> {
  const { data, error } = await client.auth.getUser();
  if (error || !data.user) redirect("/login");
  return data.user;
}
