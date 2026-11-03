import type { ReactNode } from "react";
import { logoutAction } from "../../lib/auth/actions";
import { ensureCreator } from "../../lib/auth/creator";
import { requireUser } from "../../lib/auth/session";
import { createClient } from "../../lib/supabase/server";
import { StudioNav } from "../../components/studio/StudioNav";

export default async function StudioLayout({ children }: { children: ReactNode }) {
  const supabase = await createClient();
  const user = await requireUser(supabase);
  await ensureCreator(supabase, user.id);

  return (
    <div className="shell">
      <a className="skip" href="#inhalt">
        Zum Inhalt springen
      </a>
      <aside className="sidebar">
        <p className="brand">Creator-Studio</p>
        <StudioNav />
      </aside>
      <header className="topbar">
        <span>
          Creator: <strong>{user.email}</strong>
        </span>
        <form action={logoutAction}>
          <button type="submit">Abmelden</button>
        </form>
      </header>
      <main id="inhalt" tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}
