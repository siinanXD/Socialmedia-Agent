// SIN-1387: Direkter Abruf gegen die LOKALE Supabase: Konto B auf die Datei, die Konto A im Browser hochgeladen hat.
// Aufruf: node scripts/upload-direktabruf.mjs <anon-key> <clip-pfad>; Passwörter aus der Umgebung (Infisical), nie ausgegeben.
// Staging: PRUEF_SUPABASE_URL=https://pxoqubnwjegshkxirphm.supabase.co, Konten aus SM_STAGING_A_*/SM_STAGING_B_*.
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
const [anon, clip] = process.argv.slice(2);
const url = process.env.PRUEF_SUPABASE_URL ?? "http://127.0.0.1:54321";
async function token(email, password) {
  const r = await fetch(`${url}/auth/v1/token?grant_type=password`, { method: "POST", headers: { apikey: anon, "content-type": "application/json" }, body: JSON.stringify({ email, password }) });
  return (await r.json()).access_token;
}
const env = process.env;
const a = await token(env.SM_STAGING_A_EMAIL ?? env.TESTNUTZER_EMAIL, env.SM_STAGING_A_PASSWORT ?? env.TESTNUTZER_PASSWORT);
const b = await token(env.SM_STAGING_B_EMAIL ?? "sinan-test-2@sjcode.de", env.SM_STAGING_B_PASSWORT ?? env.TESTNUTZER2_PASSWORT);
const h = (t, extra = {}) => ({ apikey: anon, authorization: `Bearer ${t}`, ...extra });
const rest = (t, q) => fetch(`${url}/rest/v1/${q}`, { headers: h(t, { "accept-profile": "social_media" }) }).then((r) => r.json());

const [asset] = await rest(a, "assets?select=id,storage_path,size_bytes,sha256&original_filename=eq.nutzerweg-testclip.mp4");
console.log("A: Asset", asset.id, asset.storage_path.replace(/[0-9a-f-]{36}/g, "<uuid>"), asset.size_bytes, "Bytes");
const obj = (t, art) => fetch(`${url}/storage/v1/object/${art}/social-media/${asset.storage_path}`, { headers: h(t) });

const ownR = await obj(a, "authenticated");
const own = Buffer.from(await ownR.arrayBuffer());
const clipSha = createHash("sha256").update(readFileSync(clip)).digest("hex");
console.log("A: Download", ownR.status, "SHA-256 gleich wie Testclip:", createHash("sha256").update(own).digest("hex") === clipSha, "| in DB gleich:", asset.sha256 === clipSha);

const bR = await obj(b, "authenticated");
console.log("B: Download authenticated", bR.status, (await bR.text()).slice(0, 80));
const pubR = await fetch(`${url}/storage/v1/object/public/social-media/${asset.storage_path}`);
console.log("anonym: öffentlicher Link", pubR.status, (await pubR.text()).slice(0, 80));
const signR = await fetch(`${url}/storage/v1/object/sign/social-media/${asset.storage_path}`, { method: "POST", headers: h(b, { "content-type": "application/json" }), body: JSON.stringify({ expiresIn: 60 }) });
console.log("B: Signed URL anfordern", signR.status, (await signR.text()).slice(0, 80));
const listR = await fetch(`${url}/storage/v1/object/list/social-media`, { method: "POST", headers: h(b, { "content-type": "application/json" }), body: JSON.stringify({ prefix: asset.storage_path.split("/").slice(0, 3).join("/") + "/" }) });
console.log("B: Ordner von A auflisten", listR.status, JSON.stringify(await listR.json()));
console.log("B: assets per id", JSON.stringify(await rest(b, `assets?id=eq.${asset.id}`)));
console.log("B: asset_rights per id", JSON.stringify(await rest(b, `asset_rights?asset_id=eq.${asset.id}`)));
console.log("B: jobs", JSON.stringify(await rest(b, "jobs?select=id")));
