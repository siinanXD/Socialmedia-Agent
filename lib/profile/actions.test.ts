import { beforeEach, describe, expect, it, vi } from "vitest";

const requireUser = vi.fn();
const saveProfile = vi.fn();
const client = {};
vi.mock("../auth/session", () => ({ requireUser: () => requireUser() }));
vi.mock("../supabase/server", () => ({ createClient: async () => client }));
vi.mock("./store", () => ({ saveProfile: (...a: unknown[]) => saveProfile(...a) }));
class Redirect extends Error {
  constructor(public url: string) {
    super(url);
  }
}
vi.mock("next/navigation", () => ({
  redirect: (url: string) => {
    throw new Redirect(url);
  },
}));

import { saveProfileAction } from "./actions";

const form = (entries: [string, string][]) => {
  const f = new FormData();
  for (const [k, v] of entries) f.append(k, v);
  return f;
};
const target = async (p: Promise<unknown>) => {
  try {
    await p;
  } catch (e) {
    if (e instanceof Redirect) return e.url;
    throw e;
  }
  return null;
};

beforeEach(() => {
  requireUser.mockReset().mockResolvedValue({ id: "u1", email: "a@b.de" });
  saveProfile.mockReset().mockResolvedValue(true);
});

describe("saveProfileAction", () => {
  it("speichert ein gültiges Profil mit der Nutzerkennung aus der Session, nicht aus dem Formular", async () => {
    const url = await target(saveProfileAction(form([["niche", "Fitness"], ["user_id", "fremd"], ["creator_id", "fremd"]])));
    expect(url).toBe("/profil?hinweis=gespeichert");
    expect(saveProfile).toHaveBeenCalledWith(client, "u1", expect.objectContaining({ niche: "Fitness", publish_enabled: false }));
    expect(JSON.stringify(saveProfile.mock.calls[0])).not.toContain("fremd");
  });

  it("lehnt ungültige Eingaben ab, ohne die Datenbank anzufassen", async () => {
    expect(await target(saveProfileAction(form([["platforms", "myspace"]])))).toBe("/profil?fehler=plattform");
    expect(await target(saveProfileAction(form([["allowed_sources", "scraping"]])))).toBe("/profil?fehler=quelle");
    expect(await target(saveProfileAction(form([["hashtags", Array.from({ length: 31 }, (_, i) => `t${i}`).join(" ")]])))).toBe(
      "/profil?fehler=hashtags_anzahl",
    );
    expect(saveProfile).not.toHaveBeenCalled();
  });

  it("meldet einen Speicherfehler nur als festen Code", async () => {
    saveProfile.mockResolvedValue(false);
    expect(await target(saveProfileAction(form([])))).toBe("/profil?fehler=speichern");
    saveProfile.mockRejectedValue(new Error("connect ECONNREFUSED 10.0.0.1:5432 password=geheim"));
    const url = await target(saveProfileAction(form([])));
    expect(url).toBe("/profil?fehler=speichern");
    expect(url).not.toContain("geheim");
  });

  it("ohne Anmeldung wird nichts gespeichert", async () => {
    requireUser.mockRejectedValue(new Redirect("/login"));
    expect(await target(saveProfileAction(form([["niche", "x"]])))).toBe("/login");
    expect(saveProfile).not.toHaveBeenCalled();
  });
});
