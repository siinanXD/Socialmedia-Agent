// SIN-1387: Upload-Ablauf unter den Rechten des Nutzers (RLS und Storage-Policies, kein service_role).
// Der Browser lädt die Datei per Signed Upload URL direkt in den Bucket; die App sieht nur Metadaten.
// Größe und MIME-Typ übernimmt `completeUpload` aus Storage, nicht aus der Anfrage. Den SHA-256 rechnet der
// Worker beim Validieren nach; bis dahin fehlen die asset_checks, und das Asset gilt nicht als verwendbar.
import type { CreatorClient } from "../auth/creator";
import { BUCKET, objectPath, parseUploadRequest, safeFilename, type UploadError } from "./validate";

type Fehler = UploadError | "dublette" | "quote" | "fehlt" | "intern";
type Result<T> = { status: 200; body: T } | { status: 400 | 409 | 413 | 500; body: { fehler: Fehler; assetId?: string } };

const UNIQUE_VIOLATION = "23505";
const QUOTA_EXCEEDED = "53400";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
// Gleiche Standardwerte wie social_media.creator_limits (SIN-1381), falls der Creator keine eigene Zeile hat.
const DEFAULT_LIMITS = { max_storage_bytes: 5 * 1024 ** 3, max_assets: 500 };

const fail = (status: 400 | 409 | 413 | 500, fehler: Fehler, assetId?: string) =>
  ({ status, body: assetId ? { fehler, assetId } : { fehler } }) as const;

async function creatorId(client: CreatorClient, userId: string): Promise<string | null> {
  const { data } = await client.from("creators").select("id").eq("user_id", userId).maybeSingle();
  return data?.id ?? null;
}

async function existingBySha(client: CreatorClient, creator: string, sha256: string): Promise<string | null> {
  const { data } = await client.from("assets").select("id").eq("creator_id", creator).eq("sha256", sha256).maybeSingle();
  return data?.id ?? null;
}

/** Prüft Anfrage, Dublette und Quote und gibt eine Signed Upload URL für einen neuen Pfad aus. */
export async function prepareUpload(
  client: CreatorClient,
  userId: string,
  body: unknown,
): Promise<Result<{ assetId: string; path: string; token: string }>> {
  const parsed = parseUploadRequest(body);
  if (!parsed.ok) return fail(400, parsed.code);
  const req = parsed.value;
  const creator = await creatorId(client, userId);
  if (!creator) return fail(500, "intern");

  const dup = await existingBySha(client, creator, req.sha256);
  if (dup) return fail(409, "dublette", dup);

  const [{ data: used, error: usedError }, { data: limits }] = await Promise.all([
    client.from("assets").select("size_bytes").eq("creator_id", creator),
    client.from("creator_limits").select("max_storage_bytes, max_assets").eq("creator_id", creator).maybeSingle(),
  ]);
  if (usedError || !used) return fail(500, "intern");
  const lim = limits ?? DEFAULT_LIMITS;
  const usedBytes = used.reduce((sum, a) => sum + Number(a.size_bytes), 0);
  if (used.length + 1 > lim.max_assets || usedBytes + req.sizeBytes > Number(lim.max_storage_bytes)) return fail(413, "quote");

  const assetId = crypto.randomUUID();
  const path = objectPath(creator, assetId, req.filename);
  const { data, error } = await client.storage.from(BUCKET).createSignedUploadUrl(path);
  if (error || !data) return fail(500, "intern");
  return { status: 200, body: { assetId, path, token: data.token } };
}

/**
 * Registriert die hochgeladene Datei: Asset, Rechte-Bestätigung und genau einen analyze-Job
 * (idempotency_key aus dem Hash). Wiederholbar: ein zweiter Aufruf liefert dasselbe Ergebnis.
 */
export async function completeUpload(
  client: CreatorClient,
  userId: string,
  body: unknown,
): Promise<Result<{ assetId: string; jobId: string }>> {
  const parsed = parseUploadRequest(body);
  if (!parsed.ok) return fail(400, parsed.code);
  const assetId = (body as { assetId?: unknown }).assetId;
  if (typeof assetId !== "string" || !UUID.test(assetId)) return fail(400, "ungueltig");
  const req = parsed.value;
  const creator = await creatorId(client, userId);
  if (!creator) return fail(500, "intern");

  const path = objectPath(creator, assetId, req.filename);
  const name = safeFilename(req.filename);
  const { data: listed } = await client.storage.from(BUCKET).list(`originals/${creator}/${assetId}`, { search: name });
  const object = listed?.find((o) => o.name === name);
  if (!object) return fail(400, "fehlt");

  const known = await existingBySha(client, creator, req.sha256);
  if (known && known !== assetId) return fail(409, "dublette", known);
  if (!known) {
    const { error } = await client.from("assets").insert({
      id: assetId,
      creator_id: creator,
      storage_path: path,
      original_filename: name,
      sha256: req.sha256,
      mime_type: object.metadata?.mimetype,
      size_bytes: object.metadata?.size,
    });
    if (error) {
      // Abgelehnte Datei nicht im Bucket liegen lassen (Quote voll, gleichzeitige Dublette).
      await client.storage.from(BUCKET).remove([path]);
      if (error.code === QUOTA_EXCEEDED) return fail(413, "quote");
      if (error.code === UNIQUE_VIOLATION) return fail(409, "dublette");
      return fail(400, "ungueltig");
    }
    const rights = await client
      .from("asset_rights")
      .insert({ asset_id: assetId, creator_id: creator, source: req.rights.source, statement: req.rights.statement });
    if (rights.error) return fail(500, "intern");
  }

  const jobId = await analyzeJob(client, creator, assetId, req.sha256);
  return jobId ? { status: 200, body: { assetId, jobId } } : fail(500, "intern");
}

async function analyzeJob(client: CreatorClient, creator: string, assetId: string, sha256: string): Promise<string | null> {
  const key = `analyze:${sha256}`;
  const inserted = await client.from("jobs").insert({ creator_id: creator, idempotency_key: key, kind: "analyze" }).select("id").single();
  if (inserted.error && inserted.error.code !== UNIQUE_VIOLATION) return null;
  if (inserted.data) {
    const link = await client.from("job_assets").insert({ job_id: inserted.data.id, asset_id: assetId, creator_id: creator });
    if (link.error) return null;
    return inserted.data.id;
  }
  const { data } = await client.from("jobs").select("id").eq("creator_id", creator).eq("idempotency_key", key).single();
  return data?.id ?? null;
}

export type AssetRow = { id: string; original_filename: string; size_bytes: number; mime_type: string; created_at: string };

/** Eigene Medien, neueste zuerst (RLS: nur der eigene Creator). */
export async function listAssets(client: CreatorClient): Promise<AssetRow[]> {
  const { data, error } = await client
    .from("assets")
    .select("id, original_filename, size_bytes, mime_type, created_at")
    .order("created_at", { ascending: false });
  if (error) throw new Error("Medien konnten nicht gelesen werden");
  return data as AssetRow[];
}
