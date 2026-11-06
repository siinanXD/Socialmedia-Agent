// SIN-1387: legt die zwei synthetischen Socialmedia-Testkonten im Staging-Projekt pxoqubnwjegshkxirphm an
// (bestätigt, ohne E-Mail-Versand). Wiederholbar: vorhandene Konten bleiben, wie sie sind.
// Adressen und Passwörter kommen aus Infisical /socialmedia-agent (SM_STAGING_A_*, SM_STAGING_B_*), der
// Management-Token aus /leitstand (SUPABASE_ACCESS_TOKEN). Gibt keine Geheimnisse aus.
//   infisical run --path=/leitstand -- infisical run --path=/socialmedia-agent -- node scripts/staging-konten.mjs
const ref = "pxoqubnwjegshkxirphm";
const keys = await (
  await fetch(`https://api.supabase.com/v1/projects/${ref}/api-keys?reveal=true`, {
    headers: { authorization: `Bearer ${process.env.SUPABASE_ACCESS_TOKEN}` },
  })
).json();
const service = keys.find((k) => k.name === "service_role")?.api_key;
if (!service) throw new Error("service_role-Schlüssel des Staging-Projekts nicht lesbar");

for (const k of ["A", "B"]) {
  const email = process.env[`SM_STAGING_${k}_EMAIL`];
  const password = process.env[`SM_STAGING_${k}_PASSWORT`];
  if (!email || !password) throw new Error(`Fehlende Umgebungsvariablen: SM_STAGING_${k}_EMAIL, SM_STAGING_${k}_PASSWORT`);
  const r = await fetch(`https://${ref}.supabase.co/auth/v1/admin/users`, {
    method: "POST",
    headers: { apikey: service, authorization: `Bearer ${service}`, "content-type": "application/json" },
    body: JSON.stringify({ email, password, email_confirm: true }),
  });
  const body = await r.json();
  const vorhanden = r.status === 422 && /already/i.test(body.msg ?? body.message ?? "");
  console.log(`Konto ${k}:`, r.status, body.id ? "angelegt" : vorhanden ? "schon vorhanden" : (body.msg ?? body.message ?? "Fehler"));
}
