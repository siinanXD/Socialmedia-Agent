"use client";

import { useActionState } from "react";
import { saveProfileAction, type ProfileState } from "../lib/profile/actions";
import { MAX_NICHE, MAX_TEXT, PLATFORMS, SOURCES, type ProfileValues } from "../lib/profile/validate";
import { SubmitButton } from "./submit-button";

const INITIAL: ProfileState = { status: "idle" };

export function ProfileForm({ initial }: { initial: ProfileValues }) {
  const [state, action] = useActionState(saveProfileAction, INITIAL);
  const e = state.errors ?? {};
  return (
    <form action={action} className="profile-form" noValidate>
      {state.message && <p role={state.status === "error" ? "alert" : "status"} className="notice">{state.message}</p>}

      <label>
        Nische
        <input name="niche" defaultValue={initial.niche} maxLength={MAX_NICHE} aria-describedby="hilfe-nische" aria-invalid={!!e.niche} />
        <small id="hilfe-nische">Dein Themenfeld (z. B. Fitness). Damit wählen wir Highlights und Hashtags passend aus.</small>
        {e.niche && <small role="alert">{e.niche}</small>}
      </label>

      <fieldset>
        <legend>Plattformen</legend>
        {PLATFORMS.map((p) => (
          <label key={p.value} className="check">
            <input type="checkbox" name="platform" value={p.value} defaultChecked={initial.platforms.includes(p.value)} /> {p.label}
          </label>
        ))}
        {e.platform && <small role="alert">{e.platform}</small>}
      </fieldset>

      <label>
        Tonalität
        <textarea name="tone" rows={3} defaultValue={initial.tone} maxLength={MAX_TEXT} aria-describedby="hilfe-ton" aria-invalid={!!e.tone} />
        <small id="hilfe-ton">Wie du klingst (z. B. motivierend, direkt). Captions und Texte richten sich danach.</small>
        {e.tone && <small role="alert">{e.tone}</small>}
      </label>

      <label>
        Zielgruppe
        <textarea name="target_audience" rows={3} defaultValue={initial.target_audience} maxLength={MAX_TEXT} aria-invalid={!!e.target_audience} />
        {e.target_audience && <small role="alert">{e.target_audience}</small>}
      </label>

      <label>
        Hashtags
        <textarea name="hashtags" rows={3} defaultValue={initial.hashtags.join(" ")} aria-describedby="hilfe-tags" aria-invalid={!!e.hashtags} />
        <small id="hilfe-tags">Durch Leerzeichen oder Komma getrennt, höchstens 30. Das # setzen wir automatisch.</small>
        {e.hashtags && <small role="alert">{e.hashtags}</small>}
      </label>

      <fieldset>
        <legend>Erlaubte Quellen</legend>
        {SOURCES.map((s) => (
          <label key={s.value} className="check">
            <input type="checkbox" name="source" value={s.value} defaultChecked={initial.allowed_sources.includes(s.value)} /> {s.label}
          </label>
        ))}
        {e.source && <small role="alert">{e.source}</small>}
      </fieldset>

      <fieldset>
        <legend>Veröffentlichen</legend>
        <label className="check">
          <input type="checkbox" name="publish_enabled" defaultChecked={initial.publish_enabled} aria-describedby="warn-publish" /> Veröffentlichen erlauben
        </label>
        <small id="warn-publish">
          Standard ist aus. Auch wenn du es einschaltest, bleibt die manuelle Freigabe Pflicht: nichts wird ohne deine Freigabe
          veröffentlicht. Jede Änderung dieses Schalters wird im Änderungsprotokoll festgehalten.
        </small>
      </fieldset>

      <SubmitButton label="Speichern" pendingLabel="Speichern …" />
    </form>
  );
}
