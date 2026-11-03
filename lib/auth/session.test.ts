import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  redirect: (path: string) => {
    throw new Error(`REDIRECT:${path}`);
  },
}));

import { requireUser } from "./session";

const clientWith = (result: unknown) => ({ auth: { getUser: async () => result } }) as never;

describe("requireUser", () => {
  it("leitet ohne Anmeldung auf /login", async () => {
    await expect(requireUser(clientWith({ data: { user: null }, error: null }))).rejects.toThrow("REDIRECT:/login");
  });
  it("leitet bei Auth-Fehler auf /login", async () => {
    await expect(requireUser(clientWith({ data: { user: null }, error: { message: "x" } }))).rejects.toThrow(
      "REDIRECT:/login",
    );
  });
  it("gibt den angemeldeten Nutzer zurück", async () => {
    const user = { id: "u1", email: "a@b.de" };
    await expect(requireUser(clientWith({ data: { user }, error: null }))).resolves.toEqual(user);
  });
});
