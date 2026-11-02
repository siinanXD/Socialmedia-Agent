import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { supabaseEnv } from "./env";

/** Supabase-Client für Server Components und Server Actions (Schema `social_media`, Rechte des angemeldeten Nutzers). */
export async function createClient() {
  const cookieStore = await cookies();
  const { url, anonKey } = supabaseEnv();
  return createServerClient(url, anonKey, {
    db: { schema: "social_media" },
    cookies: {
      getAll: () => cookieStore.getAll(),
      setAll(cookiesToSet) {
        try {
          for (const { name, value, options } of cookiesToSet) cookieStore.set(name, value, options);
        } catch {
          // Aus einer Server Component darf man keine Cookies setzen; proxy.ts frischt die Session auf.
        }
      },
    },
  });
}
