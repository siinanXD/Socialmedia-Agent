import { createClient } from "../../../lib/supabase/server";
import { prepareUpload } from "../../../lib/uploads/store";

// SIN-1387: Signed Upload URL für eine geprüfte Anfrage. Ohne Session antwortet schon proxy.ts mit 401.
export async function POST(request: Request) {
  const supabase = await createClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return Response.json({ fehler: "anmeldung" }, { status: 401 });
  const result = await prepareUpload(supabase, data.user.id, await request.json().catch(() => null));
  return Response.json(result.body, { status: result.status });
}
