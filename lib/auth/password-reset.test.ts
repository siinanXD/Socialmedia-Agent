import { beforeEach, describe, expect, it, vi } from "vitest";

const resetPasswordForEmail = vi.fn();
const updateUser = vi.fn();
const signOut = vi.fn();
const getUser = vi.fn();
vi.mock("../supabase/server", () => ({
  createClient: async () => ({ auth: { resetPasswordForEmail, updateUser, signOut, getUser } }),
}));

const jar = new Map<string, string>();
vi.mock("next/headers", () => ({
  headers: async () => new Headers({ host: "localhost:3000" }),
  cookies: async () => ({
    get: (n: string) => (jar.has(n) ? { name: n, value: jar.get(n)! } : undefined),
    delete: (n: string) => void jar.delete(n),
  }),
}));
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

import { requestResetAction, setNewPasswordAction } from "./password-reset";
import { RECOVERY_COOKIE } from "./recovery";

const form = (fields: Record<string, string>) => {
  const f = new FormData();
  for (const [k, v] of Object.entries(fields)) f.set(k, v);
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
const pw = (password: string, confirm = password) => form({ password, confirm });
const withRecovery = () => {
  jar.set(RECOVERY_COOKIE, "1");
  getUser.mockResolvedValue({ data: { user: { id: "u" } }, error: null });
};

beforeEach(() => {
  for (const m of [resetPasswordForEmail, updateUser, signOut, getUser]) m.mockReset();
  jar.clear();
});

describe("requestResetAction", () => {
  it("antwortet für bekannte und unbekannte Adresse gleich", async () => {
    resetPasswordForEmail.mockResolvedValueOnce({ error: null });
    const known = await target(requestResetAction(form({ email: "a@b.de" })));
    resetPasswordForEmail.mockResolvedValueOnce({ error: { message: "User not found a@b.de", status: 400 } });
    const unknown = await target(requestResetAction(form({ email: "x@y.de" })));
    expect(known).toBe("/passwort-vergessen?hinweis=versendet");
    expect(unknown).toBe(known);
  });

  it("gibt keine Rohmeldung weiter, auch nicht bei Fehlern", async () => {
    resetPasswordForEmail.mockResolvedValue({ error: { message: "rate limit db-host-7", status: 429 } });
    const url = await target(requestResetAction(form({ email: "a@b.de" })));
    expect(url).not.toMatch(/db-host|rate/);
  });

  it("verlangt eine Adresse und ruft sonst Supabase nicht auf", async () => {
    expect(await target(requestResetAction(form({ email: " " })))).toBe("/passwort-vergessen?fehler=email");
    expect(resetPasswordForEmail).not.toHaveBeenCalled();
  });

  it("schickt den Link über die Auth-Callback-Route", async () => {
    resetPasswordForEmail.mockResolvedValue({ error: null });
    await target(requestResetAction(form({ email: "a@b.de" })));
    expect(resetPasswordForEmail).toHaveBeenCalledWith("a@b.de", {
      redirectTo: "http://localhost:3000/auth/callback",
    });
  });
});

describe("setNewPasswordAction", () => {
  it("leitet ohne Recovery-Markierung auf /login, ohne Supabase aufzurufen", async () => {
    expect(await target(setNewPasswordAction(pw("langes-passwort")))).toBe("/login");
    expect(updateUser).not.toHaveBeenCalled();
  });

  it("leitet ohne gültige Session auf /login", async () => {
    jar.set(RECOVERY_COOKIE, "1");
    getUser.mockResolvedValue({ data: { user: null }, error: new Error("x") });
    expect(await target(setNewPasswordAction(pw("langes-passwort")))).toBe("/login");
    expect(updateUser).not.toHaveBeenCalled();
  });

  it("lehnt zu kurzes Passwort ab", async () => {
    withRecovery();
    expect(await target(setNewPasswordAction(pw("kurz")))).toBe("/passwort-neu?fehler=passwort");
    expect(updateUser).not.toHaveBeenCalled();
  });

  it("lehnt abweichende Wiederholung ab", async () => {
    withRecovery();
    expect(await target(setNewPasswordAction(pw("langes-passwort", "anderes-passwort")))).toBe(
      "/passwort-neu?fehler=wiederholung",
    );
  });

  it("setzt das Passwort, meldet ab und leitet auf /login", async () => {
    withRecovery();
    updateUser.mockResolvedValue({ error: null });
    expect(await target(setNewPasswordAction(pw("langes-passwort")))).toBe("/login?hinweis=zurueckgesetzt");
    expect(updateUser).toHaveBeenCalledWith({ password: "langes-passwort" });
    expect(signOut).toHaveBeenCalled();
    expect(jar.has(RECOVERY_COOKIE)).toBe(false);
  });

  it("zeigt bei Supabase-Fehler nur einen festen Code", async () => {
    withRecovery();
    updateUser.mockResolvedValue({ error: { message: "same password db-host-7", status: 422 } });
    expect(await target(setNewPasswordAction(pw("langes-passwort")))).toBe("/passwort-neu?fehler=speichern");
  });
});
