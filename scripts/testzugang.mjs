// SIN-1445: Beispieldaten für die zwei Testkonten (nur diese beiden). Idempotent; --reset stellt den Anfangsstand her.
// Läuft lokal mit service_role-Schlüssel aus der Umgebung (Infisical); der Schlüssel gehört nie in die App oder ins Repo.
//   SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... TESTNUTZER_PASSWORT=... TESTNUTZER2_PASSWORT=... node scripts/testzugang.mjs [--reset]
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";

export const ACCOUNTS = [
  { email: "sinan-test@sjcode.de", passwordEnv: "TESTNUTZER_PASSWORT", name: "Sinan Test", prefix: "a" },
  { email: "sinan-test-2@sjcode.de", passwordEnv: "TESTNUTZER2_PASSWORT", name: "Sinan Test 2", prefix: "b" },
];

const sha = (s) => createHash("sha256").update(s).digest("hex");

// Erfundene Beispiele: keine echten Dateien, keine Videos Dritter. storage_path zeigt auf nichts.
function sampleAssets(prefix) {
  return [
    ["beispiel-training.mp4", "video/mp4", 52428800, "freigegeben"],
    ["beispiel-ernaehrung.mp4", "video/mp4", 31457280, "wartet_auf_freigabe"],
    ["beispiel-foto.jpg", "image/jpeg", 2097152, "abgelehnt"],
  ].map(([name, mime, size, status]) => ({
    storage_path: `testzugang/${prefix}/${name}`,
    original_filename: name,
    sha256: sha(`testzugang:${prefix}:${name}`),
    mime_type: mime,
    size_bytes: size,
    approval_status: status,
  }));
}

function sampleJobs(prefix) {
  return [
    { idempotency_key: `testzugang-${prefix}-1`, status: "queued", params: { art: "reel", beispiel: true } },
    { idempotency_key: `testzugang-${prefix}-2`, status: "queued", params: { art: "karussell", beispiel: true } },
  ];
}

export async function runTestzugang(store, { reset = false, env = process.env } = {}) {
  const report = [];
  for (const acc of ACCOUNTS) {
    const userId = await store.ensureUser(acc.email, env[acc.passwordEnv]);
    const creatorId = await store.upsertCreator(userId, acc.name);
    report.push(`${acc.email}: Profil (Creator ${acc.name}) vorhanden`);
    if (reset) {
      for (const t of ["assets", "jobs"]) if (await store.tableExists(t)) await store.deleteSampleData(creatorId, t);
    }
    if (await store.tableExists("assets")) {
      await store.insertAssetsIfMissing(creatorId, sampleAssets(acc.prefix));
      report.push(`${acc.email}: assets befüllt`);
    } else report.push(`${acc.email}: assets übersprungen (Tabelle fehlt)`);
    if (await store.tableExists("jobs")) {
      await store.insertJobsIfMissing(creatorId, sampleJobs(acc.prefix));
      report.push(`${acc.email}: jobs befüllt`);
    } else report.push(`${acc.email}: jobs übersprungen (Tabelle fehlt)`);
  }
  return report;
}

// Adapter auf Supabase (service_role). Jede Abfrage ist auf creator_id bzw. die zwei E-Mails begrenzt.
export async function supabaseStore(env = process.env) {
  const { createClient } = await import("@supabase/supabase-js");
  const url = env.SUPABASE_URL ?? env.NEXT_PUBLIC_SUPABASE_URL;
  const key = env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) throw new Error("SUPABASE_URL und SUPABASE_SERVICE_ROLE_KEY fehlen (aus Infisical, nicht ins Repo)");
  const admin = createClient(url, key, { auth: { persistSession: false } });
  const db = admin.schema("social_media");
  const allowed = new Set(ACCOUNTS.map((a) => a.email));
  const fail = (what, e) => {
    throw new Error(`${what}: ${e.message}`);
  };
  return {
    async ensureUser(email, password) {
      if (!allowed.has(email)) throw new Error("Konto nicht erlaubt");
      for (let page = 1; ; page++) {
        const { data, error } = await admin.auth.admin.listUsers({ page, perPage: 200 });
        if (error) fail("Nutzer lesen", error);
        const hit = data.users.find((u) => u.email === email);
        if (hit) return hit.id;
        if (data.users.length < 200) break;
      }
      if (!password) throw new Error(`Konto ${email} fehlt und kein Passwort in der Umgebung`);
      const { data, error } = await admin.auth.admin.createUser({ email, password, email_confirm: true });
      if (error) fail("Nutzer anlegen", error);
      return data.user.id;
    },
    async upsertCreator(userId, name) {
      const { data, error } = await db
        .from("creators")
        .upsert({ user_id: userId, display_name: name }, { onConflict: "user_id" })
        .select("id")
        .single();
      if (error) fail("Creator", error);
      return data.id;
    },
    async tableExists(t) {
      const { error } = await db.from(t).select("id").limit(1);
      if (!error) return true;
      if (error.code === "42P01" || error.code === "PGRST205") return false;
      fail(`Tabelle ${t}`, error);
    },
    async insertAssetsIfMissing(creatorId, rows) {
      const { error } = await db
        .from("assets")
        .upsert(rows.map((r) => ({ ...r, creator_id: creatorId })), { onConflict: "creator_id,sha256", ignoreDuplicates: true });
      if (error) fail("assets", error);
    },
    async insertJobsIfMissing(creatorId, rows) {
      const { error } = await db
        .from("jobs")
        .upsert(rows.map((r) => ({ ...r, creator_id: creatorId })), { onConflict: "creator_id,idempotency_key", ignoreDuplicates: true });
      if (error) fail("jobs", error);
    },
    async deleteSampleData(creatorId, table) {
      const { error } = await db.from(table).delete().eq("creator_id", creatorId);
      if (error) fail(`${table} löschen`, error);
    },
  };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const report = await runTestzugang(await supabaseStore(), { reset: process.argv.includes("--reset") });
  console.log(report.join("\n"));
}
