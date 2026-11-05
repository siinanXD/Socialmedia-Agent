import { beforeEach, describe, expect, it, vi } from "vitest";

const exchangeCodeForSession = vi.fn();
vi.mock("../../../lib/supabase/server", () => ({
  createClient: async () => ({ auth: { exchangeCodeForSession } }),
}));

import { GET } from "./route";

const call = (qs: string) => GET(new Request(`http://localhost:3000/auth/callback${qs}`));
beforeEach(() => exchangeCodeForSession.mockReset());

describe("GET /auth/callback", () => {
  it("tauscht den Code serverseitig und leitet auf /passwort-neu mit Markierung", async () => {
    exchangeCodeForSession.mockResolvedValue({ error: null });
    const res = await call("?code=abc");
    expect(exchangeCodeForSession).toHaveBeenCalledWith("abc");
    expect(new URL(res.headers.get("location")!).pathname).toBe("/passwort-neu");
    expect(res.headers.get("set-cookie")).toMatch(/sm_recovery=1.*HttpOnly/i);
  });

  it("leitet ohne Code mit festem Code zurück", async () => {
    const res = await call("");
    expect(res.headers.get("location")).toMatch(/\/passwort-vergessen\?fehler=link$/);
    expect(exchangeCodeForSession).not.toHaveBeenCalled();
  });

  it("zeigt bei Fehler des Austauschs keine Rohmeldung und setzt keine Markierung", async () => {
    exchangeCodeForSession.mockResolvedValue({ error: { message: "otp expired db-host-7" } });
    const res = await call("?code=bad");
    const loc = res.headers.get("location")!;
    expect(loc).toMatch(/\/passwort-vergessen\?fehler=link$/);
    expect(loc).not.toMatch(/db-host|otp/);
    expect(res.headers.get("set-cookie")).toBeNull();
  });
});
