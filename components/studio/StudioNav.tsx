"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AREAS, isActive } from "../../lib/studio/areas";

export function StudioNavList({ pathname }: { pathname: string }) {
  return (
    <ul className="nav-list">
      {AREAS.map((area) => (
        <li key={area.href}>
          <Link href={area.href} aria-current={isActive(pathname, area.href) ? "page" : undefined}>
            <span className="nav-nr" aria-hidden="true">
              {area.nr}
            </span>
            {area.label}
          </Link>
        </li>
      ))}
    </ul>
  );
}

export function StudioNav() {
  return (
    <nav aria-label="Hauptnavigation">
      <StudioNavList pathname={usePathname()} />
    </nav>
  );
}
