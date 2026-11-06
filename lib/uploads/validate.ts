// SIN-1387: Prüfung einer Upload-Anfrage, bevor die App eine Signed Upload URL ausgibt.
// Gleiche Grenzen wie der Bucket `social-media` (SIN-1380) und die CHECKs in social_media (SIN-1381).

export const BUCKET = "social-media";
export const MAX_UPLOAD_BYTES = 500 * 1024 * 1024;
export const ALLOWED_MIME = ["video/mp4", "video/quicktime", "image/jpeg", "image/png"] as const;
export const RIGHTS_SOURCES = ["own", "licensed", "reference"] as const;
const MAX_STATEMENT = 2000;

export type UploadRequest = {
  filename: string;
  mimeType: (typeof ALLOWED_MIME)[number];
  sizeBytes: number;
  sha256: string;
  rights: { source: (typeof RIGHTS_SOURCES)[number]; statement: string };
};

export type UploadError = "ungueltig" | "typ" | "groesse" | "rechte";

const isIn = <T extends string>(list: readonly T[], v: unknown): v is T => list.includes(v as T);

export function parseUploadRequest(body: unknown): { ok: true; value: UploadRequest } | { ok: false; code: UploadError } {
  if (typeof body !== "object" || body === null) return { ok: false, code: "ungueltig" };
  const b = body as Record<string, unknown>;
  if (typeof b.filename !== "string" || typeof b.sha256 !== "string" || !/^[0-9a-f]{64}$/.test(b.sha256)) {
    return { ok: false, code: "ungueltig" };
  }
  if (!isIn(ALLOWED_MIME, b.mimeType)) return { ok: false, code: "typ" };
  if (typeof b.sizeBytes !== "number" || !Number.isInteger(b.sizeBytes) || b.sizeBytes < 1 || b.sizeBytes > MAX_UPLOAD_BYTES) {
    return { ok: false, code: "groesse" };
  }
  const r = b.rights as Record<string, unknown> | undefined;
  const statement = typeof r?.statement === "string" ? r.statement.trim() : "";
  if (!r || !isIn(RIGHTS_SOURCES, r.source) || statement.length < 1 || statement.length > MAX_STATEMENT) {
    return { ok: false, code: "rechte" };
  }
  return {
    ok: true,
    value: { filename: b.filename, mimeType: b.mimeType, sizeBytes: b.sizeBytes, sha256: b.sha256, rights: { source: r.source, statement } },
  };
}

/** Nur der letzte Pfadteil, nur Buchstaben, Ziffern, Punkt, Bindestrich und Unterstrich; nie leer, nie `..`. */
export function safeFilename(name: string): string {
  const base = name.split(/[\\/]/).pop() ?? "";
  const cleaned = base.replace(/[^\p{L}\p{N}._-]+/gu, "_").replace(/^\.+/, "").slice(-200);
  return cleaned === "" ? "datei" : cleaned;
}

export function objectPath(creatorId: string, assetId: string, filename: string): string {
  return `originals/${creatorId}/${assetId}/${safeFilename(filename)}`;
}
