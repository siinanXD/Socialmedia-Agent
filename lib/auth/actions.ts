"use server";

import { redirect } from "next/navigation";
import { createClient } from "../supabase/server";

const MIN_PASSWORD_LENGTH = 8;

function credentials(formData: FormData): { email: string; password: string } {
  const email = formData.get("email");
  const password = formData.get("password");
  return {
    email: typeof email === "string" ? email.trim() : "",
    password: typeof password === "string" ? password : "",
  };
}

// Fehler laufen nur als fester Code in die URL; die Meldung von Supabase wird verworfen.
export async function loginAction(formData: FormData): Promise<void> {
  const { email, password } = credentials(formData);
  if (!email || !password) redirect("/login?fehler=eingabe");

  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) redirect("/login?fehler=anmeldung");
  redirect("/");
}

export async function registerAction(formData: FormData): Promise<void> {
  const { email, password } = credentials(formData);
  if (!email || !password) redirect("/registrieren?fehler=eingabe");
  if (password.length < MIN_PASSWORD_LENGTH) redirect("/registrieren?fehler=passwort");

  const supabase = await createClient();
  const { data, error } = await supabase.auth.signUp({ email, password });
  if (error) redirect("/registrieren?fehler=registrierung");
  // Mit E-Mail-Bestätigung gibt es noch keine Session.
  if (!data.session) redirect("/login?hinweis=bestaetigen");
  redirect("/");
}

export async function logoutAction(): Promise<void> {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/login");
}
