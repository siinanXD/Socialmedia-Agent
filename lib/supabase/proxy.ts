import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { supabaseEnv } from "./env";

const PUBLIC_PATHS = ["/login", "/registrieren"];

/**
 * Frischt die Session auf und schützt alle Routen außer den öffentlichen.
 * Geprüft wird mit getUser() beim Auth-Server; dem Cookie allein wird nicht getraut.
 */
export async function updateSession(request: NextRequest): Promise<NextResponse> {
  let response = NextResponse.next({ request });
  const { url, anonKey } = supabaseEnv();

  const supabase = createServerClient(url, anonKey, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll(cookiesToSet) {
        for (const { name, value } of cookiesToSet) request.cookies.set(name, value);
        response = NextResponse.next({ request });
        for (const { name, value, options } of cookiesToSet) response.cookies.set(name, value, options);
      },
    },
  });

  const { data, error } = await supabase.auth.getUser();
  const signedIn = !error && data.user !== null;
  const { pathname } = request.nextUrl;
  const isPublic = PUBLIC_PATHS.includes(pathname);

  if (!signedIn && !isPublic) return redirectTo(request, "/login", response);
  if (signedIn && isPublic) return redirectTo(request, "/", response);
  return response;
}

function redirectTo(request: NextRequest, path: string, from: NextResponse): NextResponse {
  const redirect = NextResponse.redirect(new URL(path, request.url));
  // Aufgefrischte Session-Cookies mitgeben.
  for (const cookie of from.cookies.getAll()) redirect.cookies.set(cookie);
  return redirect;
}
