import type { ReactNode } from "react";

/** Ehrlicher Leerzustand: sagt, dass der Bereich noch nicht gebaut ist. */
export function EmptyState({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="empty-state" aria-labelledby="bereich-titel">
      <h1 id="bereich-titel">{title}</h1>
      <p className="badge">Geplant</p>
      <p>{children}</p>
      <p className="muted">Noch keine Daten.</p>
    </section>
  );
}
