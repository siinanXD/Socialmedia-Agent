import type { ReactNode } from "react";
import { logoutAction } from "../../lib/auth/actions";
import { requireUser } from "../../lib/auth/session";
import { Navigation } from "../../components/navigation";

export default async function StudioLayout({ children }: { children: ReactNode }) {
  const user = await requireUser();
  return (
    <div className="shell">
      <a className="skip" href="#inhalt">
        Zum Inhalt springen
      </a>
      <aside className="sidebar">
        <p className="brand">Creator-Studio</p>
        <Navigation />
      </aside>
      <header className="topbar">
        <span>{user.email}</span>
        <form action={logoutAction}>
          <button type="submit">Abmelden</button>
        </form>
      </header>
      <main id="inhalt" className="content">
        {children}
      </main>
    </div>
  );
}
