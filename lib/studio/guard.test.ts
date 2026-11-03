import { beforeEach, describe, expect, it, vi } from "vitest";

const { redirect, getUser, ensureCreator } = vi.hoisted(() => ({
  redirect: vi.fn((to: string) => {
    throw new Error("REDIRECT:" + to);
  }),
  getUser: vi.fn(),
  ensureCreator: vi.fn(),
}));

vi.mock("next/navigation", () => ({ redirect }));
vi.mock("../supabase/server", () => ({
  createClient: async () => ({ auth: { getUser } }),
}));
vi.mock("../auth/creator", () => ({ ensureCreator }));

import { requireStudioUser } from "./guard";

describe("requireStudioUser", () => {
  beforeEach(() => vi.clearAllMocks());

  it("leitet nicht angemeldete Nutzer auf /login", async () => {
    getUser.mockResolvedValue({ data: { user: null }, error: null });
    await expect(requireStudioUser()).rejects.toThrow("REDIRECT:/login");
    expect(ensureCreator).not.toHaveBeenCalled();
  });

  it("leitet bei Auth-Fehler auf /login", async () => {
    getUser.mockResolvedValue({ data: { user: null }, error: { message: "x" } });
    await expect(requireStudioUser()).rejects.toThrow("REDIRECT:/login");
  });

  it("gibt den Nutzer zurück und legt den Creator an", async () => {
    getUser.mockResolvedValue({ data: { user: { id: "u1", email: "a@b.de" } }, error: null });
    const user = await requireStudioUser();
    expect(user.email).toBe("a@b.de");
    expect(ensureCreator).toHaveBeenCalledWith(expect.anything(), "u1");
  });
});
