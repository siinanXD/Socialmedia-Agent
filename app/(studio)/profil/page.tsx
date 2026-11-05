import { SubmitButton } from "../../../components/submit-button";
import { requireUser } from "../../../lib/auth/session";
import { saveProfileAction } from "../../../lib/profile/actions";
import { profileMessage } from "../../../lib/profile/messages";
import { loadProfile } from "../../../lib/profile/store";
import { MAX_NICHE, MAX_TEXT, PLATFORMS, SOURCES, type ProfileValues } from "../../../lib/profile/validate";
import { createClient } from "../../../lib/supabase/server";

const LEER: ProfileValues = {
  niche: "",
  tone: "",
  target_audience: "",
  platforms: [],
  allowed_sources: [],
  hashtags: [],
  publish_enabled: false,
};

export default async function ProfilPage({
  searchParams,
}: {
  searchParams: Promise<{ fehler?: string; hinweis?: string }>;
}) {
  const user = await requireUser();
  const params = await searchParams;
  let profile: ProfileValues;
  try {
    profile = (await loadProfile(await createClient(), user.id)) ?? LEER;
  } catch {
    // Kein Formular ohne geladene Werte: ein leeres Formular würde ein vorhandenes Profil überschreiben.
    return (
      <>
        <h1>Profil</h1>
        <p role="alert" className="profile-message error">
          {profileMessage({ fehler: "laden" })?.text}
        </p>
      </>
    );
  }
  const message = profileMessage(params);

  return (
    <>
      <h1>Profil</h1>
      <p className="profile-intro">
        Hier legst du fest, für wen und wie das Studio arbeitet. Die Angaben gelten für alle deine Medien und Aufträge und
        lassen sich jederzeit ändern.
      </p>
      {message && (
        <p role={message.kind === "error" ? "alert" : "status"} className={`profile-message ${message.kind}`}>
          {message.text}
        </p>
      )}
      <form action={saveProfileAction} className="profile">
        <section aria-labelledby="p-marke">
          <h2 id="p-marke">Marke</h2>
          <label>
            Nische
            <input name="niche" defaultValue={profile.niche} maxLength={MAX_NICHE} placeholder="z. B. Fitness" />
            <small>
              Das Thema deiner Inhalte. Es steuert, welche Szenen als Highlight zählen und welche Vorschläge zu dir passen.
            </small>
          </label>
          <label>
            Tonalität
            <textarea name="tone" defaultValue={profile.tone} maxLength={MAX_TEXT} rows={3} placeholder="z. B. locker, direkt, motivierend" />
            <small>Wie deine Beschriftungen und Texte klingen sollen.</small>
          </label>
          <label>
            Zielgruppe
            <textarea
              name="target_audience"
              defaultValue={profile.target_audience}
              maxLength={MAX_TEXT}
              rows={3}
              placeholder="z. B. Einsteiger zwischen 18 und 30"
            />
            <small>Für wen du Inhalte machst.</small>
          </label>
          <label>
            Hashtags
            <textarea name="hashtags" defaultValue={profile.hashtags.join(" ")} rows={2} placeholder="#fitness #gym #workout" />
            <small>Höchstens 30, durch Leerzeichen oder Komma getrennt. Das # setzt das Studio selbst.</small>
          </label>
        </section>

        <section role="group" aria-labelledby="p-plattformen">
          <h2 id="p-plattformen">Plattformen</h2>
          <p className="hint">Auf welchen Plattformen du Inhalte zeigen willst. Es wird nichts automatisch dorthin gesendet.</p>
          {PLATFORMS.map((p) => (
            <label key={p.value} className="check">
              <input type="checkbox" name="platforms" value={p.value} defaultChecked={profile.platforms.includes(p.value)} />
              {p.label}
            </label>
          ))}
        </section>

        <section role="group" aria-labelledby="p-quellen">
          <h2 id="p-quellen">Erlaubte Quellen</h2>
          <p className="hint">Woher das Studio Material und Anregungen beziehen darf. Ohne Häkchen nutzt es keine davon.</p>
          {SOURCES.map((s) => (
            <label key={s.value} className="check">
              <input type="checkbox" name="allowed_sources" value={s.value} defaultChecked={profile.allowed_sources.includes(s.value)} />
              {s.label}
            </label>
          ))}
        </section>

        <section role="group" aria-labelledby="p-veroeffentlichen" className="publish">
          <h2 id="p-veroeffentlichen">Veröffentlichen</h2>
          <label className="check">
            <input type="checkbox" name="publish_enabled" defaultChecked={profile.publish_enabled} />
            Veröffentlichen erlauben
          </label>
          <p className="hint warn">
            Standard ist aus. Der Schalter erlaubt später das Veröffentlichen über freigegebene Schnittstellen, ersetzt aber nie
            deine Freigabe: Jeder Beitrag braucht weiterhin deine ausdrückliche Bestätigung. Jede Änderung an diesem Schalter wird
            mit Zeitpunkt und Nutzer protokolliert.
          </p>
        </section>

        <SubmitButton label="Profil speichern" pendingLabel="Wird gespeichert …" />
      </form>
    </>
  );
}
