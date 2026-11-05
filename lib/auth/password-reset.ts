"use server";

import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { createClient } from "../supabase/server";
import { RECOVERY_COOKIE } from "./recovery";

const MIN_PASSWORD_LENGTH = 8;


function field(formData: FormData, name: string): string {
  const value = formData.get(name);
  return typeof value === "string" ? value : "";
}

// Die Antwort ist immer dieselbe, egal ob die Adresse bekannt ist oder Supabase einen Fehler meldet.
export async function requestResetAction(formData: FormData): Promise<void> {
  const email = field(formData, "email").trim();
  if (!email) redirect("/passwort-vergessen?fehler=email");

  const requestHeaders = await headers();
  const host = requestHeaders.get("x-forwarded-host") ?? requestHeaders.get("host") ?? "localhost:3000";
  const proto = requestHeaders.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");

  const supabase = await createClient();
  // Ergebnis bewusst verworfen: kein Hinweis, ob das Konto existiert.
  await supabase.auth.resetPasswordForEmail(email, { redirectTo: `${proto}://${host}/auth/callback` });
  redirect("/passwort-vergessen?hinweis=versendet");
}

export async function setNewPasswordAction(formData: FormData): Promise<void> {
  const cookieStore = await cookies();
  if (!cookieStore.get(RECOVERY_COOKIE)) redirect("/login");

  const supabase = await createClient();
  const { data, error: userError } = await supabase.auth.getUser();
  if (userError || !data.user) redirect("/login");

  const password = field(formData, "password");
  if (password.length < MIN_PASSWORD_LENGTH) redirect("/passwort-neu?fehler=passwort");
  if (password !== field(formData, "confirm")) redirect("/passwort-neu?fehler=wiederholung");

  const { error } = await supabase.auth.updateUser({ password });
  if (error) redirect("/passwort-neu?fehler=speichern");

  await supabase.auth.signOut();
  cookieStore.delete(RECOVERY_COOKIE);
  redirect("/login?hinweis=zurueckgesetzt");
}
