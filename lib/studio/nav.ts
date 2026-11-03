export type NavItem = { href: string; label: string; number: string };

export const NAV_ITEMS: readonly NavItem[] = [
  { href: "/mediathek", label: "Mediathek", number: "01" },
  { href: "/highlights", label: "Szenen und Highlights", number: "02" },
  { href: "/auftraege", label: "Aufträge", number: "03" },
  { href: "/freigabe", label: "Freigabe und Export", number: "04" },
];

/** Aktiv ist die Route selbst und alles darunter, aber kein bloß ähnlicher Präfix. */
export function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(href + "/");
}
