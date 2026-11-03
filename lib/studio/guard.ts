import { redirect } from "next/navigation";
import { ensureCreator } from "../auth/creator";
import { createClient } from "../supabase/server";

/**
 * Serverseitige Anmeldeprüfung für alle Studio-Seiten (zusätzlich zu proxy.ts):
 * fragt den Auth-Server, leitet sonst auf /login und legt den Creator an.
 */
export async function requireStudioUser(): Promise<{ id: string; email: string }> {
  const supabase = await createClient();
  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user) redirect("/login");

  await ensureCreator(supabase, data.user.id);
  return { id: data.user.id, email: data.user.email ?? "" };
}
