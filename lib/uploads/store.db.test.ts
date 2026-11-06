// SIN-1387: Upload Ende zu Ende gegen die lokale Supabase mit Storage-API und Bucket `social-media`
// (Migration aus supabase/tests/pending_migrations lokal eingespielt, siehe README „Upload lokal prüfen“):
//   SUPABASE_TEST_URL=http://127.0.0.1:54321 SUPABASE_TEST_ANON_KEY=<anon key aus `supabase status`> npm test
// Ohne diese Werte (CI ohne Storage-API) wird übersprungen.
import { createClient } from "@supabase/supabase-js";
import { describe, expect, it } from "vitest";
import { ensureCreator, type CreatorClient } from "../auth/creator";
import { completeUpload, listAssets, prepareUpload } from "./store";
import { BUCKET } from "./validate";

const url = process.env.SUPABASE_TEST_URL;
const anon = process.env.SUPABASE_TEST_ANON_KEY;

async function newUser(): Promise<{ client: CreatorClient; userId: string }> {
  const client = createClient(url!, anon!, { db: { schema: "social_media" }, auth: { persistSession: false } }) as unknown as CreatorClient;
  const { data, error } = await client.auth.signUp({ email: `upload-${crypto.randomUUID()}@example.test`, password: "test-passwort-1234" });
  if (error || !data.user || !data.session) throw new Error("Testnutzer konnte nicht angelegt werden");
  await ensureCreator(client, data.user.id);
  return { client, userId: data.user.id };
}

async function sha256(bytes: Uint8Array<ArrayBuffer>): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

describe.skipIf(!url || !anon)("Upload gegen lokale Supabase", () => {
  it("A lädt hoch und sieht den Eintrag; Wiederholung erzeugt keinen zweiten Job; B sieht und lädt nichts", async () => {
    const a = await newUser();
    const b = await newUser();
    const bytes = new TextEncoder().encode(`clip-${crypto.randomUUID()}`);
    const request = {
      filename: "../training clip.mp4",
      mimeType: "video/mp4",
      sizeBytes: bytes.length,
      sha256: await sha256(bytes),
      rights: { source: "own", statement: "Selbst gefilmt." },
    };

    const prepared = await prepareUpload(a.client, a.userId, request);
    expect(prepared.status).toBe(200);
    if (prepared.status !== 200) return;
    expect(prepared.body.path).toMatch(/^originals\/[0-9a-f-]{36}\/[0-9a-f-]{36}\/training_clip\.mp4$/);
    const up = await a.client.storage
      .from(BUCKET)
      .uploadToSignedUrl(prepared.body.path, prepared.body.token, bytes, { contentType: "video/mp4" });
    expect(up.error).toBeNull();

    const done = await completeUpload(a.client, a.userId, { ...request, assetId: prepared.body.assetId });
    expect(done.status).toBe(200);
    const again = await completeUpload(a.client, a.userId, { ...request, assetId: prepared.body.assetId });
    expect(again).toEqual(done);

    const assets = await listAssets(a.client);
    expect(assets.map((x) => [x.id, x.original_filename, x.size_bytes])).toEqual([
      [prepared.body.assetId, "training_clip.mp4", bytes.length],
    ]);
    const jobs = await a.client.from("jobs").select("kind, idempotency_key");
    expect(jobs.data).toEqual([{ kind: "analyze", idempotency_key: `analyze:${request.sha256}` }]);
    const rights = await a.client.from("asset_rights").select("source");
    expect(rights.data).toEqual([{ source: "own" }]);

    // Dublette: derselbe Inhalt noch einmal → 409 mit vorhandener Asset-ID, keine neue URL
    expect(await prepareUpload(a.client, a.userId, request)).toEqual({
      status: 409,
      body: { fehler: "dublette", assetId: prepared.body.assetId },
    });

    // B: weder Eintrag noch Datei, auch nicht mit dem genauen Pfad
    expect(await listAssets(b.client)).toEqual([]);
    const direct = await b.client.storage.from(BUCKET).download(prepared.body.path);
    expect(direct.data).toBeNull();
    const signed = await b.client.storage.from(BUCKET).createSignedUrl(prepared.body.path, 60);
    expect(signed.data).toBeNull();
    // B kann A's hochgeladenes Asset nicht unter eigenem Namen registrieren
    expect((await completeUpload(b.client, b.userId, { ...request, assetId: prepared.body.assetId })).status).toBe(400);

    // A selbst lädt die Datei herunter (Gegenprobe)
    const own = await a.client.storage.from(BUCKET).download(prepared.body.path);
    expect(new Uint8Array(await own.data!.arrayBuffer())).toEqual(bytes);
  });

  it("ohne hochgeladene Datei wird nichts registriert", async () => {
    const a = await newUser();
    const request = {
      filename: "fehlt.mp4",
      mimeType: "video/mp4",
      sizeBytes: 10,
      sha256: "b".repeat(64),
      rights: { source: "own", statement: "x" },
    };
    const prepared = await prepareUpload(a.client, a.userId, request);
    if (prepared.status !== 200) throw new Error("prepare fehlgeschlagen");
    expect((await completeUpload(a.client, a.userId, { ...request, assetId: prepared.body.assetId })).status).toBe(400);
    expect(await listAssets(a.client)).toEqual([]);
  });
});
