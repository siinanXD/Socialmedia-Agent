import { afterEach, describe, expect, it, vi } from "vitest";
import { supabaseEnv } from "./env";

afterEach(() => vi.unstubAllEnvs());

describe("supabaseEnv", () => {
  it("liefert URL und anon-Schlüssel", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "http://127.0.0.1:54321");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "anon");
    expect(supabaseEnv()).toEqual({ url: "http://127.0.0.1:54321", anonKey: "anon" });
  });

  it("nennt bei fehlendem Wert nur den Variablennamen", () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "geheim");
    expect(() => supabaseEnv()).toThrow("NEXT_PUBLIC_SUPABASE_URL");
    expect(() => supabaseEnv()).not.toThrow(/geheim/);
  });
});
