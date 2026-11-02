// SIN-1196: Migrationen laufen nach Merge ins gemeinsame Supabase-Projekt und dürfen nur das Schema `social_media` ändern.
// Aufruf: node scripts/check-migration-schemas.mjs [Ordner]   (Standard: supabase/migrations)
// Lesende Verweise (auth.users als Fremdschlüssel, auth.uid() in Policies) bleiben erlaubt; geprüft wird das Ziel jeder Anweisung.
// shortcut: Regex-Prüfung der Anweisungsziele, kein SQL-Parser; Funktionskörper ($$…$$) werden nicht geprüft und `do`-Blöcke abgelehnt.
// Die harte Grenze ist die Datenbankrolle des Workflows; bei Lücken dort nachziehen, nicht hier.
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const ident = String.raw`(?:"[^"]+"|[a-z_][a-z0-9_$]*)`;
const name = String.raw`${ident}(?:\s*\.\s*${ident})?`;
const nameRe = new RegExp(`^(${ident})(?:\\s*\\.\\s*(${ident}))?`, "i");
const objectKinds = "table|view|materialized\\s+view|sequence|type|function|procedure|domain";

// Kommentare, Zeichenketten und $$-Körper entfernen, damit `;` und Schemanamen darin nichts auslösen.
function strip(sql) {
  return sql
    .replace(/\/\*[\s\S]*?\*\//g, " ")
    .replace(/--[^\n]*/g, " ")
    .replace(/(\$[a-z_]*\$)[\s\S]*?\1/gi, "$$$$")
    .replace(/'(?:[^']|'')*'/g, "''");
}

const isSocialMedia = (s) => (s.startsWith('"') ? s === '"social_media"' : s.toLowerCase() === "social_media");

// Ziel `schema.objekt` muss im Schema social_media liegen; unqualifiziert landet es per search_path in public.
function targetOk(text) {
  const m = nameRe.exec(text.trim());
  return Boolean(m && m[2] && isSocialMedia(m[1]));
}
const schemaOk = (text) => isSocialMedia(text.trim().split(/[\s,]/)[0]);
const listOk = (text, ok = targetOk) => text.split(",").every((part) => ok(part));

const kind = (re) => new RegExp(`^${re}`, "i");
const rules = [
  [kind(String.raw`create\s+schema\s+(?:if\s+not\s+exists\s+)?(${name})`), schemaOk],
  [kind(String.raw`alter\s+schema\s+(${name})`), schemaOk],
  [kind(String.raw`create\s+(?:or\s+replace\s+)?(?:(?:unlogged|temporary|temp|recursive)\s+)*(?:${objectKinds})\s+(?:if\s+not\s+exists\s+)?(${name})`), targetOk],
  [kind(String.raw`alter\s+(?:${objectKinds})\s+(?:if\s+exists\s+)?(?:only\s+)?(${name})`), targetOk],
  [kind(String.raw`drop\s+(?:${objectKinds}|index)\s+(?:concurrently\s+)?(?:if\s+exists\s+)?([^;]*?)(?:\s+(?:cascade|restrict))?$`), (t) => listOk(t)],
  [kind(String.raw`(?:create|alter|drop)\s+(?:or\s+replace\s+)?(?:policy|trigger)\s+(?:if\s+exists\s+)?${ident}\s+(?:\w+\s+)*?on\s+(${name})`), targetOk],
  [kind(String.raw`create\s+(?:unique\s+)?index\s+(?:concurrently\s+)?(?:if\s+not\s+exists\s+)?(?:${ident}\s+)?on\s+(?:only\s+)?(${name})`), targetOk],
  [kind(String.raw`comment\s+on\s+\w+\s+(${name})`), targetOk],
  [kind(String.raw`insert\s+into\s+(${name})`), targetOk],
  [kind(String.raw`update\s+(?:only\s+)?(${name})`), targetOk],
  [kind(String.raw`delete\s+from\s+(?:only\s+)?(${name})`), targetOk],
  [kind(String.raw`truncate\s+(?:table\s+)?(?:only\s+)?([^;]+?)(?:\s+(?:restart|continue|cascade|restrict).*)?$`), (t) => listOk(t)],
];

function grantTargetOk(stmt) {
  const m = /^(?:grant|revoke)\b[\s\S]*?\bon\s+([\s\S]*?)\s+(?:to|from)\s/i.exec(stmt);
  if (!m) return false; // Rollenmitgliedschaft (grant r to s) ändert Rechte außerhalb von social_media
  const spec = m[1].trim();
  const inSchema = /^all\s+\w+\s+in\s+schema\s+([\s\S]+)$/i.exec(spec) ?? /^schema\s+([\s\S]+)$/i.exec(spec);
  if (inSchema) return listOk(inSchema[1], schemaOk);
  return listOk(spec.replace(/^(?:table|sequence|function|procedure|type|domain)\s+/i, ""));
}

function statementOk(stmt) {
  if (/^(?:grant|revoke)\b/i.test(stmt)) return grantTargetOk(stmt);
  if (/^drop\s+schema\b/i.test(stmt)) return false; // nie, auch nicht für social_media
  const rule = rules.find(([re]) => re.test(stmt));
  if (!rule) return false; // do, create extension/role, set, select, with … sind in Migrationen nicht vorgesehen
  const [re, ok] = rule;
  return ok(re.exec(stmt)[1] ?? stmt);
}

function violations(sql) {
  return strip(sql)
    .split(";")
    .map((s) => s.trim().replace(/\s+/g, " "))
    .filter((s) => s && !statementOk(s));
}

const dir = process.argv[2] ?? "supabase/migrations";
let failed = false;
for (const file of readdirSync(dir).filter((f) => f.endsWith(".sql")).sort()) {
  for (const stmt of violations(readFileSync(join(dir, file), "utf8"))) {
    failed = true;
    console.error(`${file}: nur Schema social_media ist erlaubt, abgelehnt: ${stmt.slice(0, 120)}`);
  }
}
process.exit(failed ? 1 : 0);
