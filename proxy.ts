import type { NextRequest } from "next/server";
import { updateSession } from "./lib/supabase/proxy";

export async function proxy(request: NextRequest) {
  return updateSession(request);
}

export const config = {
  // Statische Dateien und der Health-Check bleiben ohne Anmeldung erreichbar.
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api/health).*)"],
};
