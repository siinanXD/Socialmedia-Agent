import { beforeEach, describe, expect, it, vi } from "vitest";

const { getUser, redirect } = vi.hoisted(() => ({
  getUser: vi.fn(),
  redirect: vi.fn((url: string) => {
    throw new Error(`REDIRECT:${url}`);
  }),
}));
vi.mock("next/navigation", () => ({ redirect, usePathname: () => "/mediathek" }));
vi.mock("../../lib/supabase/server", () => ({ createClient: async () => ({ auth: { getUser } }) }));
vi.mock("../../lib/auth/creator", () => ({ ensureCreator: vi.fn() }));
vi.mock("../../lib/auth/actions", () => ({ logoutAction: vi.fn() }));

import StudioLayout from "./layout";

describe("StudioLayout", () => {
  beforeEach(() => vi.clearAllMocks());

  it("leitet nicht angemeldete Nutzer auf /login", async () => {
    getUser.mockResolvedValue({ data: { user: null }, error: null });
    await expect(StudioLayout({ children: null })).rejects.toThrow("REDIRECT:/login");
  });

  it("leitet bei Auth-Fehler auf /login", async () => {
    getUser.mockResolvedValue({ data: { user: { id: "u", email: "a@b.de" } }, error: new Error("x") });
    await expect(StudioLayout({ children: null })).rejects.toThrow("REDIRECT:/login");
  });

  it("rendert für angemeldete Nutzer", async () => {
    getUser.mockResolvedValue({ data: { user: { id: "u", email: "a@b.de" } }, error: null });
    await expect(StudioLayout({ children: null })).resolves.toBeTruthy();
  });
});
