import { beforeEach, describe, expect, it, vi } from "vitest";

const { redirect, getUser, ensureCreator } = vi.hoisted(() => ({
  redirect: vi.fn((to: string) => {
    throw new Error("REDIRECT:" + to);
  }),
  getUser: vi.fn(),
  ensureCreator: vi.fn(),
}));
vi.mock("next/navigation", () => ({ redirect }));
vi.mock("../supabase/server", () => ({ createClient: async () => ({ auth: { getUser } }) }));
vi.mock("./creator", () => ({ ensureCreator }));

import { requireUser } from "./session";

beforeEach(() => vi.clearAllMocks());

describe("requireUser", () => {
  it("leitet nicht angemeldete Nutzer auf /login", async () => {
    getUser.mockResolvedValue({ data: { user: null }, error: null });
    await expect(requireUser()).rejects.toThrow("REDIRECT:/login");
    expect(ensureCreator).not.toHaveBeenCalled();
  });
  it("leitet bei Auth-Fehler auf /login", async () => {
    getUser.mockResolvedValue({ data: { user: null }, error: { message: "x" } });
    await expect(requireUser()).rejects.toThrow("REDIRECT:/login");
  });
  it("liefert die E-Mail und stellt den Creator sicher", async () => {
    getUser.mockResolvedValue({ data: { user: { id: "u1", email: "a@b.de" } }, error: null });
    await expect(requireUser()).resolves.toEqual({ id: "u1", email: "a@b.de" });
    expect(ensureCreator).toHaveBeenCalledWith(expect.anything(), "u1");
  });
});
