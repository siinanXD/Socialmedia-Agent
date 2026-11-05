"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "../supabase/server";
import { saveProfile } from "./save";
import { parseProfileForm, type FieldErrors } from "./validate";

export type ProfileState = { status: "idle" | "saved" | "error"; message?: string; errors?: FieldErrors };

/** Server Action: validiert serverseitig, schreibt mit dem Anmelde-Token des Nutzers (RLS, kein Service-Role-Schlüssel). */
export async function saveProfileAction(_prev: ProfileState, formData: FormData): Promise<ProfileState> {
  const parsed = parseProfileForm(formData);
  if (!parsed.ok) return { status: "error", message: "Bitte die markierten Felder prüfen.", errors: parsed.errors };

  const supabase = await createClient();
  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user) return { status: "error", message: "Bitte erneut anmelden." };

  try {
    await saveProfile(supabase, data.user.id, parsed.values);
  } catch {
    // Keine internen Details an den Browser.
    return { status: "error", message: "Das Profil konnte nicht gespeichert werden. Bitte versuche es später noch einmal." };
  }
  revalidatePath("/profil");
  return { status: "saved", message: "Profil gespeichert." };
}
