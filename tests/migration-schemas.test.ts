import { execFileSync, spawnSync } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, test } from "vitest";

// SIN-1196: dasselbe Skript prüft in CI jede Migration, bevor sie nach main ins gemeinsame Supabase-Projekt läuft.
const script = "scripts/check-migration-schemas.mjs";

function check(sql: string) {
  const dir = mkdtempSync(join(tmpdir(), "migrations-"));
  writeFileSync(join(dir, "20261030000000_test.sql"), sql);
  return spawnSync("node", [script, dir], { encoding: "utf8" });
}

test("die vorhandenen Migrationen bestehen den Check", () => {
  expect(() => execFileSync("node", [script, "supabase/migrations"])).not.toThrow();
});

describe("erlaubt", () => {
  test.each([
    "create table social_media.x (id uuid primary key references auth.users (id));",
    'alter table "social_media"."x" enable row level security;',
    "create policy p on social_media.x for select to authenticated using ((select auth.uid()) = id);",
    "grant select on social_media.x to authenticated;",
    "grant usage on schema social_media to authenticated;",
    "create index i on social_media.x (id);\n-- drop table public.x;\n/* alter table auth.users */",
    "insert into social_media.x (a) values ('public.x; drop table auth.users');",
    "create function social_media.f() returns int language sql as $$ select 1; $$;",
  ])("%s", (sql) => {
    expect(check(sql).status).toBe(0);
  });
});

describe("abgelehnt", () => {
  test.each([
    "create table public.x (id int);",
    "create table x (id int);",
    "alter table auth.users add column y int;",
    "drop table storage.objects;",
    "create policy p on public.x for select using (true);",
    "create index i on stromlauf.runs (id);",
    "grant select on all tables in schema public to anon;",
    "grant select on public.x to anon;",
    "insert into public.x values (1);",
    "update auth.users set email = null;",
    "delete from public.x;",
    "truncate social_media.x, public.y;",
    "create schema stromlauf;",
    "drop schema social_media cascade;",
    "alter schema public rename to x;",
    "create extension pgcrypto;",
    "create role r;",
    "set search_path = public;",
    "do $$ begin drop table public.x; end $$;",
    "create table social_media.x (id int);\ndrop table public.x;",
  ])("%s", (sql) => {
    const result = check(sql);
    expect(result.status).toBe(1);
    expect(result.stderr).toContain("20261030000000_test.sql");
  });
});
