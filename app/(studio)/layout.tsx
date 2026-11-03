import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { logoutAction } from "../../lib/auth/actions";
import { ensureCreator } from "../../lib/auth/creator";
import { creatorLabel } from "../../lib/studio/nav";
import { createClient } from "../../lib/supabase/server";
import { Nav } from "../../components/studio/Nav";

export default async function StudioLayout({ children }: { children: ReactNode }) {
  const supabase = await createClient();
  // Serverseitig beim Auth-Server prüfen, nicht nur dem Cookie trauen (zusätzlich zu proxy.ts).
  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user) redirect("/login");

  await ensureCreator(supabase, data.user.id);
  const { data: creator } = await supabase
    .from("creators")
    .select("display_name")
    .eq("user_id", data.user.id)
    .maybeSingle();
  const label = creatorLabel(creator?.display_name, data.user.email ?? "Creator");

  return (
    <div className="shell">
      <a href="#inhalt" className="skip-link">Zum Inhalt springen</a>
      <aside className="sidebar">
        <p className="brand">Socialmedia-Agent</p>
        <Nav />
      </aside>
      <div className="main-col">
        <header className="topbar">
          <span className="creator" title={label}>{label}</span>
          <form action={logoutAction}>
            <button type="submit" className="btn">Abmelden</button>
          </form>
        </header>
        <main id="inhalt" tabIndex={-1}>{children}</main>
      </div>
    </div>
  );
}
