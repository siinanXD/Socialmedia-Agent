import { isActive, SECTIONS } from "../../lib/studio/sections";

export function NavList({ pathname }: { pathname: string }) {
  return (
    <nav aria-label="Hauptnavigation" className="studio-nav">
      <ul>
        {SECTIONS.map((s) => (
          <li key={s.href}>
            <a href={s.href} aria-current={isActive(pathname, s.href) ? "page" : undefined}>
              <span className="studio-nav-nummer" aria-hidden="true">{s.nummer}</span>
              {s.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
