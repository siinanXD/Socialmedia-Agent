"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createClient } from "../lib/supabase/client";
import { ALLOWED_MIME, BUCKET } from "../lib/uploads/validate";

const MELDUNG: Record<string, string> = {
  typ: "Nur MP4, MOV, JPEG oder PNG.",
  groesse: "Die Datei ist leer oder größer als 500 MB.",
  rechte: "Bitte bestätige deine Rechte an der Datei.",
  dublette: "Diese Datei liegt schon in deiner Mediathek.",
  quote: "Dein Speicherplatz ist voll.",
  anmeldung: "Bitte melde dich neu an.",
};
const ALLGEMEIN = "Hochladen hat nicht geklappt. Bitte versuche es noch einmal.";

async function sha256(file: File): Promise<string> {
  // shortcut: liest die ganze Datei in den Speicher; bei Dateien nahe 500 MB auf stückweises Hashen umstellen.
  const digest = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

async function post(url: string, body: unknown): Promise<{ ok: boolean; data: Record<string, string> }> {
  const res = await fetch(url, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
  return { ok: res.ok, data: await res.json().catch(() => ({})) };
}

/** Lädt eine Datei direkt in den privaten Bucket (Signed Upload URL) und registriert sie danach. */
export function UploadForm() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const file = form.get("datei");
    if (!(file instanceof File) || file.size === 0) return setMessage({ kind: "error", text: MELDUNG.groesse });
    setBusy(true);
    setMessage(null);
    try {
      const request = {
        filename: file.name,
        mimeType: file.type,
        sizeBytes: file.size,
        sha256: await sha256(file),
        rights: { source: form.get("quelle"), statement: form.get("erklaerung") },
      };
      const prepared = await post("/api/uploads", request);
      if (!prepared.ok) return setMessage({ kind: "error", text: MELDUNG[prepared.data.fehler] ?? ALLGEMEIN });
      const upload = await createClient()
        .storage.from(BUCKET)
        .uploadToSignedUrl(prepared.data.path, prepared.data.token, file, { contentType: file.type });
      if (upload.error) return setMessage({ kind: "error", text: ALLGEMEIN });
      const done = await post("/api/uploads/complete", { ...request, assetId: prepared.data.assetId });
      if (!done.ok) return setMessage({ kind: "error", text: MELDUNG[done.data.fehler] ?? ALLGEMEIN });
      setMessage({ kind: "ok", text: `„${file.name}“ ist hochgeladen und wird geprüft.` });
      event.currentTarget?.reset();
      router.refresh();
    } catch {
      setMessage({ kind: "error", text: ALLGEMEIN });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="profile upload" aria-labelledby="upload-titel">
      <h2 id="upload-titel">Datei hochladen</h2>
      <label>
        Datei
        <input type="file" name="datei" required accept={ALLOWED_MIME.join(",")} />
        <small>MP4, MOV, JPEG oder PNG, höchstens 500 MB. Die Datei bleibt privat.</small>
      </label>
      <label>
        Herkunft
        <select name="quelle" required defaultValue="own">
          <option value="own">Selbst aufgenommen</option>
          <option value="licensed">Lizenziert</option>
          <option value="reference">Nur als Referenz</option>
        </select>
      </label>
      <label>
        Rechte-Bestätigung
        <textarea name="erklaerung" required maxLength={2000} rows={2} placeholder="z. B. Selbst gefilmt, alle Personen im Bild sind einverstanden." />
        <small>Ohne Bestätigung verarbeitet das Studio die Datei nicht.</small>
      </label>
      {message && (
        <p role={message.kind === "error" ? "alert" : "status"} className={`profile-message ${message.kind}`}>
          {message.text}
        </p>
      )}
      <button type="submit" disabled={busy} aria-busy={busy}>
        {busy && <span className="spinner" aria-hidden="true" />}
        {busy ? "Wird hochgeladen …" : "Hochladen"}
      </button>
    </form>
  );
}
