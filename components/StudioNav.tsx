"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS, isActive } from "../lib/studio/nav";

export function StudioNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Bereiche" className="studio-nav">
      <ul>
        {NAV_ITEMS.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <li key={item.href}>
              <Link href={item.href} aria-current={active ? "page" : undefined}>
                <span className="nav-number" aria-hidden="true">
                  {item.number}
                </span>
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
