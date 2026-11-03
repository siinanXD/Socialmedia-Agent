import type { ReactNode } from "react";

export function EmptyState({
  number,
  title,
  status,
  children,
}: {
  number: string;
  title: string;
  status: string;
  children: ReactNode;
}) {
  return (
    <section aria-labelledby="seitentitel">
      <p className="eyebrow">Bereich {number}</p>
      <h1 id="seitentitel">{title}</h1>
      <div className="empty">
        <span className="badge">{status}</span>
        <p>{children}</p>
      </div>
    </section>
  );
}
