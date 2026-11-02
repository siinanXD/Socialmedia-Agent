import { beforeEach, describe, expect, it, vi } from "vitest";

const signInWithPassword = vi.fn();
const signUp = vi.fn();
const signOut = vi.fn();
vi.mock("../supabase/server", () => ({
  createClient: async () => ({ auth: { signInWithPassword, signUp, signOut } }),
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

import { loginAction, logoutAction, registerAction } from "./actions";

const form = (email: string, password: string) => {
  const f = new FormData();
  f.set("email", email);
  f.set("password", password);
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
  signInWithPassword.mockReset();
  signUp.mockReset();
  signOut.mockReset();
});

describe("loginAction", () => {
  it("leitet bei Erfolg auf / weiter", async () => {
    signInWithPassword.mockResolvedValue({ error: null });
    expect(await target(loginAction(form("a@b.de", "passwort1")))).toBe("/");
  });

  it("zeigt bei Fehler nur einen festen Code, nie die Rohmeldung", async () => {
    signInWithPassword.mockResolvedValue({
      error: { message: "Invalid login credentials for a@b.de at db-host-7", status: 400 },
    });
    const url = await target(loginAction(form("a@b.de", "falsch")));
    expect(url).toBe("/login?fehler=anmeldung");
    expect(url).not.toMatch(/db-host|a@b/);
  });

  it("ruft Supabase bei leerer Eingabe gar nicht erst auf", async () => {
    expect(await target(loginAction(form("", "")))).toBe("/login?fehler=eingabe");
    expect(signInWithPassword).not.toHaveBeenCalled();
  });
});

describe("registerAction", () => {
  it("leitet mit Session auf / weiter", async () => {
    signUp.mockResolvedValue({ data: { session: { access_token: "t" } }, error: null });
    expect(await target(registerAction(form("a@b.de", "passwort123")))).toBe("/");
  });

  it("verweist ohne Session (E-Mail-Bestätigung) auf /login mit Hinweis", async () => {
    signUp.mockResolvedValue({ data: { session: null }, error: null });
    expect(await target(registerAction(form("a@b.de", "passwort123")))).toBe("/login?hinweis=bestaetigen");
  });

  it("lehnt zu kurze Passwörter vor dem Aufruf ab", async () => {
    expect(await target(registerAction(form("a@b.de", "kurz")))).toBe("/registrieren?fehler=passwort");
    expect(signUp).not.toHaveBeenCalled();
  });

  it("verrät bei Fehler nicht, ob die Adresse schon existiert", async () => {
    signUp.mockResolvedValue({
      data: { session: null },
      error: { message: "User already registered", status: 422 },
    });
    expect(await target(registerAction(form("a@b.de", "passwort123")))).toBe("/registrieren?fehler=registrierung");
  });
});

describe("logoutAction", () => {
  it("meldet ab und leitet auf /login", async () => {
    signOut.mockResolvedValue({ error: null });
    expect(await target(logoutAction())).toBe("/login");
    expect(signOut).toHaveBeenCalledOnce();
  });
});
