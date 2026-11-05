import { NextResponse } from "next/server";
import { RECOVERY_COOKIE } from "../../../lib/auth/recovery";
import { createClient } from "../../../lib/supabase/server";

/** Tauscht den PKCE-Code aus dem Reset-Link serverseitig gegen eine Session. Ziel ist fest, kein `next`-Parameter. */
export async function GET(request: Request): Promise<NextResponse> {
  const { origin, searchParams } = new URL(request.url);
  const code = searchParams.get("code");
  const failure = () => NextResponse.redirect(`${origin}/passwort-vergessen?fehler=link`);
  if (!code) return failure();

  const supabase = await createClient();
  const { error } = await supabase.auth.exchangeCodeForSession(code);
  if (error) return failure();

  const response = NextResponse.redirect(`${origin}/passwort-neu`);
  response.cookies.set(RECOVERY_COOKIE, "1", {
    httpOnly: true,
    sameSite: "lax",
    secure: origin.startsWith("https:"),
    path: "/",
    maxAge: 600,
  });
  return response;
}
