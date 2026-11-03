import type { ReactNode } from "react";
import { logoutAction } from "../../lib/auth/actions";
import { requireStudioUser } from "../../lib/studio/guard";
import { StudioNav } from "../../components/StudioNav";

export default async function StudioLayout({ children }: { children: ReactNode }) {
  const user = await requireStudioUser();
  return (
    <div className="studio">
      <a className="skip-link" href="#inhalt">
        Zum Inhalt springen
      </a>
      <aside className="studio-side">
        <p className="brand">Creator-Studio</p>
        <StudioNav />
      </aside>
      <div className="studio-main">
        <header className="studio-header">
          <span>{user.email}</span>
          <form action={logoutAction}>
            <button type="submit">Abmelden</button>
          </form>
        </header>
        <main id="inhalt" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  );
}
