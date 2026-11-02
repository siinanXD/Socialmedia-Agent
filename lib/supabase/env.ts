/** Öffentliche Supabase-Werte. Nur der anon-Schlüssel; der service_role-Schlüssel gehört nie in die App. */
export function supabaseEnv(): { url: string; anonKey: string } {
  // Direkter Zugriff, damit Next die NEXT_PUBLIC_-Werte ins Client-Bundle einsetzt.
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url) throw new Error("NEXT_PUBLIC_SUPABASE_URL fehlt");
  if (!anonKey) throw new Error("NEXT_PUBLIC_SUPABASE_ANON_KEY fehlt");
  return { url, anonKey };
}
