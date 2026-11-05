"use server";

import { redirect } from "next/navigation";
import { requireUser } from "../auth/session";
import { createClient } from "../supabase/server";
import { saveProfile } from "./store";
import { parseProfileForm } from "./validate";

// Fehler laufen nur als fester Code in die URL; Meldungen der Datenbank werden verworfen.
export async function saveProfileAction(formData: FormData): Promise<void> {
  const user = await requireUser();
  const parsed = parseProfileForm(formData);
  if (!parsed.ok) redirect(`/profil?fehler=${parsed.code}`);

  let saved = false;
  try {
    // Rechte des angemeldeten Nutzers (RLS), kein Service-Role-Schlüssel.
    saved = await saveProfile(await createClient(), user.id, parsed.values);
  } catch {
    saved = false;
  }
  redirect(saved ? "/profil?hinweis=gespeichert" : "/profil?fehler=speichern");
}
