import type { ReactNode } from "react";
import { redirect } from "next/navigation";
import { logoutAction } from "../../lib/auth/actions";
import { ensureCreator } from "../../lib/auth/creator";
import { createClient } from "../../lib/supabase/server";
import { Nav } from "../../components/studio/nav";

export default async function StudioLayout({ children }: { children: ReactNode }) {
  const supabase = await createClient();
  // Serverseitig beim Auth-Server prüfen, nicht nur dem Cookie trauen (zusätzlich zu proxy.ts).
  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user) redirect("/login");

  await ensureCreator(supabase, data.user.id);

  return (
    <div className="studio">
      <a className="skip-link" href="#inhalt">Zum Inhalt springen</a>
      <aside className="studio-side">
        <p className="studio-brand">Creator-Studio</p>
        <Nav />
      </aside>
      <div className="studio-main">
        <header className="studio-head">
          <span>Creator: {data.user.email}</span>
          <form action={logoutAction}>
            <button type="submit">Abmelden</button>
          </form>
        </header>
        <main id="inhalt" tabIndex={-1}>{children}</main>
      </div>
    </div>
  );
}
