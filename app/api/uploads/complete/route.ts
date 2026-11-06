import { createClient } from "../../../../lib/supabase/server";
import { completeUpload } from "../../../../lib/uploads/store";

// SIN-1387: registriert die hochgeladene Datei (Asset, Rechte, analyze-Job). Wiederholbar.
export async function POST(request: Request) {
  const supabase = await createClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return Response.json({ fehler: "anmeldung" }, { status: 401 });
  const result = await completeUpload(supabase, data.user.id, await request.json().catch(() => null));
  return Response.json(result.body, { status: result.status });
}
