import { redirect } from "next/navigation";
import { createClient } from "../supabase/server";
import { ensureCreator } from "./creator";

/**
 * Prüft serverseitig beim Auth-Server (nicht nur am Cookie) und leitet sonst auf /login.
 * Stellt außerdem sicher, dass es die Creator-Zeile gibt.
 */
export async function requireUser(): Promise<{ id: string; email: string }> {
  const supabase = await createClient();
  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user) redirect("/login");

  await ensureCreator(supabase, data.user.id);
  return { id: data.user.id, email: data.user.email ?? "" };
}
