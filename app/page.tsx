import { redirect } from "next/navigation";
import { logoutAction } from "../lib/auth/actions";
import { ensureCreator } from "../lib/auth/creator";
import { createClient } from "../lib/supabase/server";

export default async function Home() {
  const supabase = await createClient();
  // Serverseitig beim Auth-Server prüfen, nicht nur dem Cookie trauen (zusätzlich zu proxy.ts).
  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user) redirect("/login");

  await ensureCreator(supabase, data.user.id);

  return (
    <main>
      <h1>Socialmedia-Agent</h1>
      <p>Angemeldet als {data.user.email}.</p>
      <form action={logoutAction}>
        <button type="submit">Abmelden</button>
      </form>
    </main>
  );
}
