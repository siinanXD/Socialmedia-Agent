import Link from "next/link";
import { isActive, SECTIONS } from "../lib/studio/sections";

export function NavLinks({ pathname }: { pathname: string }) {
  return (
    <ul className="nav-list">
      {SECTIONS.map((s) => (
        <li key={s.href}>
          <Link href={s.href} className="nav-link" aria-current={isActive(pathname, s.href) ? "page" : undefined}>
            {s.label}
          </Link>
        </li>
      ))}
    </ul>
  );
}
