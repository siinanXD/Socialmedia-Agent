"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS, isActiveRoute } from "../../lib/studio/nav";

export function Nav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Hauptnavigation" className="nav">
      <ul>
        {NAV_ITEMS.map((item) => {
          const active = isActiveRoute(pathname, item.href);
          return (
            <li key={item.href}>
              <Link href={item.href} aria-current={active ? "page" : undefined} className="nav-link">
                <span className="nav-number" aria-hidden="true">{item.number}</span>
                <span>{item.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
