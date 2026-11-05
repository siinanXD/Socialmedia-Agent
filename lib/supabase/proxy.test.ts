import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const getUser = vi.fn();
vi.mock("@supabase/ssr", () => ({
  createServerClient: vi.fn(() => ({ auth: { getUser } })),
}));

import { updateSession } from "./proxy";

const req = (path: string) => new NextRequest(`http://localhost:3000${path}`);

beforeEach(() => {
  getUser.mockReset();
  vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "http://127.0.0.1:54321");
  vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "anon");
});

describe("updateSession", () => {
  it("leitet ohne Session von / auf /login um", async () => {
    getUser.mockResolvedValue({ data: { user: null }, error: null });
    const res = await updateSession(req("/"));
    expect(res.status).toBe(307);
    expect(new URL(res.headers.get("location")!).pathname).toBe("/login");
  });

  it("leitet auch bei Fehler der Serverprüfung um (Cookie allein genügt nicht)", async () => {
    getUser.mockResolvedValue({ data: { user: null }, error: new Error("jwt expired") });
    const res = await updateSession(req("/irgendwas"));
    expect(new URL(res.headers.get("location")!).pathname).toBe("/login");
  });

  it("lässt angemeldete Nutzer durch", async () => {
    getUser.mockResolvedValue({ data: { user: { id: "u1" } }, error: null });
    const res = await updateSession(req("/"));
    expect(res.status).toBe(200);
    expect(res.headers.get("location")).toBeNull();
  });

  it.each(["/login", "/registrieren"])("lässt %s ohne Session offen", async (path) => {
    getUser.mockResolvedValue({ data: { user: null }, error: null });
    const res = await updateSession(req(path));
    expect(res.status).toBe(200);
  });

  it("lässt /passwort-vergessen ohne Session offen", async () => {
    getUser.mockResolvedValue({ data: { user: null }, error: null });
    expect((await updateSession(req("/passwort-vergessen"))).status).toBe(200);
  });

  it.each(["/passwort-neu", "/auth/callback"])("lässt %s ohne Session durch (die Seite prüft selbst)", async (path) => {
    getUser.mockResolvedValue({ data: { user: null }, error: null });
    expect((await updateSession(req(path))).status).toBe(200);
  });

  it("schickt Nutzer mit Recovery-Session nicht von /passwort-neu weg", async () => {
    getUser.mockResolvedValue({ data: { user: { id: "u1" } }, error: null });
    expect((await updateSession(req("/passwort-neu"))).status).toBe(200);
  });

  it("schickt angemeldete Nutzer von /login auf /", async () => {
    getUser.mockResolvedValue({ data: { user: { id: "u1" } }, error: null });
    const res = await updateSession(req("/login"));
    expect(new URL(res.headers.get("location")!).pathname).toBe("/");
  });
});
