import { ProfileForm } from "../../../components/profile-form";
import { requireUser } from "../../../lib/auth/session";
import { loadProfile } from "../../../lib/profile/save";
import type { ProfileValues } from "../../../lib/profile/validate";
import { createClient } from "../../../lib/supabase/server";

// Restriktive Standardwerte, wie in der Datenbank: nichts gewählt, Veröffentlichen aus.
const EMPTY: ProfileValues = {
  niche: "", platforms: [], tone: "", target_audience: "", hashtags: [], allowed_sources: [], publish_enabled: false,
};

export default async function Page() {
  const user = await requireUser();
  const supabase = await createClient();
  let profile: ProfileValues | null = null;
  let loadFailed = false;
  try {
    profile = await loadProfile(supabase, user.id);
  } catch {
    loadFailed = true;
  }
  return (
    <>
      <h1>Profil</h1>
      <p>Hier legst du fest, für wen und wie Inhalte entstehen. Veröffentlicht wird nie automatisch.</p>
      {loadFailed ? (
        <p role="alert">Das Profil konnte nicht geladen werden. Bitte lade die Seite neu.</p>
      ) : (
        <ProfileForm initial={profile ?? EMPTY} />
      )}
    </>
  );
}
