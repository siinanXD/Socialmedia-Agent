import { describe, expect, test } from "vitest";
import { ACCOUNTS, runTestzugang } from "./testzugang.mjs";

type Row = Record<string, unknown>;

// In-Memory-Ersatz für die Datenbank; merkt sich, welche Creator angefasst werden.
function fakeStore(opts: { missingTables?: string[] } = {}) {
  const users = new Map<string, string>(); // email -> userId
  const creators = new Map<string, { id: string; name: string }>(); // userId -> creator
  const assets: Row[] = [];
  const jobs: Row[] = [];
  const touched = new Set<string>();
  let n = 0;
  const store = {
    async ensureUser(email: string) {
      if (!users.has(email)) users.set(email, `u${++n}`);
      return users.get(email)!;
    },
    async upsertCreator(userId: string, name: string) {
      if (!creators.has(userId)) creators.set(userId, { id: `c${++n}`, name });
      touched.add(creators.get(userId)!.id);
      return creators.get(userId)!.id;
    },
    async tableExists(t: string) {
      return !(opts.missingTables ?? []).includes(t);
    },
    async insertAssetsIfMissing(creatorId: string, rows: Row[]) {
      touched.add(creatorId);
      for (const r of rows)
        if (!assets.some((a) => a.creator_id === creatorId && a.sha256 === r.sha256)) assets.push({ ...r, creator_id: creatorId });
    },
    async insertJobsIfMissing(creatorId: string, rows: Row[]) {
      touched.add(creatorId);
      for (const r of rows)
        if (!jobs.some((j) => j.creator_id === creatorId && j.idempotency_key === r.idempotency_key)) jobs.push({ ...r, creator_id: creatorId });
    },
    async deleteSampleData(creatorId: string, table: string) {
      touched.add(creatorId);
      const list = table === "assets" ? assets : jobs;
      for (let i = list.length - 1; i >= 0; i--) if (list[i].creator_id === creatorId) list.splice(i, 1);
    },
  };
  return { store, users, creators, assets, jobs, touched };
}

const snapshot = (f: ReturnType<typeof fakeStore>) => JSON.stringify([f.assets, f.jobs, [...f.creators]]);
const own = (f: ReturnType<typeof fakeStore>, id: string) =>
  JSON.stringify([f.assets.filter((a) => a.creator_id === id), f.jobs.filter((j) => j.creator_id === id)]);

describe("Testzugang", () => {
  test("zweimal ausführen ergibt denselben Stand", async () => {
    const f = fakeStore();
    await runTestzugang(f.store, {});
    const first = snapshot(f);
    await runTestzugang(f.store, {});
    expect(snapshot(f)).toBe(first);
    expect(f.assets.length).toBeGreaterThan(0);
    expect(f.jobs.length).toBeGreaterThan(0);
  });

  test("fasst nur die beiden Testkonten an, Daten anderer Konten bleiben gleich", async () => {
    const f = fakeStore();
    const other = await f.store.ensureUser("fremd@example.com");
    const otherCreator = await f.store.upsertCreator(other, "Fremd");
    await f.store.insertAssetsIfMissing(otherCreator, [{ sha256: "a".repeat(64) }]);
    await f.store.insertJobsIfMissing(otherCreator, [{ idempotency_key: "x" }]);
    f.touched.clear();
    const before = own(f, otherCreator);

    await runTestzugang(f.store, {});
    await runTestzugang(f.store, { reset: true });

    expect(f.touched.has(otherCreator)).toBe(false);
    expect(own(f, otherCreator)).toBe(before);
    const emails = ACCOUNTS.map((a: { email: string }) => a.email);
    expect([...f.users.keys()].sort()).toEqual([...emails, "fremd@example.com"].sort());
  });

  test("beide Konten haben getrennte Creator mit eigenen Daten", async () => {
    const f = fakeStore();
    await runTestzugang(f.store, {});
    const ids = [...f.creators.values()].map((c) => c.id);
    expect(new Set(ids).size).toBe(2);
    expect(new Set(f.assets.map((a) => a.sha256)).size).toBe(f.assets.length);
  });

  test("Reset stellt den Anfangsstand wieder her", async () => {
    const f = fakeStore();
    await runTestzugang(f.store, {});
    const first = snapshot(f);
    f.assets.push({ creator_id: [...f.creators.values()][0].id, sha256: "b".repeat(64) });
    f.jobs.length = 0;
    await runTestzugang(f.store, { reset: true });
    expect(snapshot(f)).toBe(first);
  });

  test("fehlende Tabellen werden übersprungen und genannt", async () => {
    const f = fakeStore({ missingTables: ["assets", "jobs"] });
    const report: string[] = await runTestzugang(f.store, {});
    expect(f.assets).toHaveLength(0);
    expect(report.join("\n")).toMatch(/assets übersprungen/);
    expect(report.join("\n")).toMatch(/jobs übersprungen/);
  });
});
