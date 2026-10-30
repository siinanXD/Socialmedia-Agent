import { describe, expect, it } from "vitest";
import { ensureCreator, type CreatorClient } from "./creator";

/** In-Memory-Ersatz für social_media.creators: user_id ist eindeutig (Fehler 23505). */
function fakeClient(opts: { insertError?: { code: string } } = {}) {
  const rows: { id: string; user_id: string }[] = [];
  const client = {
    from: () => ({
      select: () => ({
        eq: (_col: string, userId: string) => ({
          maybeSingle: async () => ({
            data: rows.find((r) => r.user_id === userId) ?? null,
            error: null,
          }),
        }),
      }),
      insert: async (row: { user_id: string }) => {
        if (opts.insertError) return { error: opts.insertError };
        if (rows.some((r) => r.user_id === row.user_id)) return { error: { code: "23505" } };
        rows.push({ id: `c${rows.length + 1}`, user_id: row.user_id });
        return { error: null };
      },
    }),
  };
  return { client: client as unknown as CreatorClient, rows };
}

describe("ensureCreator", () => {
  it("legt beim ersten Aufruf eine Zeile an", async () => {
    const { client, rows } = fakeClient();
    await ensureCreator(client, "u1");
    expect(rows).toHaveLength(1);
  });

  it("zweimal aufgerufen ergibt genau eine Zeile", async () => {
    const { client, rows } = fakeClient();
    await ensureCreator(client, "u1");
    await ensureCreator(client, "u1");
    expect(rows).toHaveLength(1);
  });

  it("trennt Nutzer: zweiter Nutzer bekommt eine eigene Zeile", async () => {
    const { client, rows } = fakeClient();
    await ensureCreator(client, "u1");
    await ensureCreator(client, "u2");
    expect(rows.map((r) => r.user_id)).toEqual(["u1", "u2"]);
  });

  it("wirft bei Datenbankfehler ohne Details der Rohmeldung", async () => {
    const { client } = fakeClient({ insertError: { code: "42501" } });
    await expect(ensureCreator(client, "u1")).rejects.toThrow("Creator konnte nicht angelegt werden");
  });
});
