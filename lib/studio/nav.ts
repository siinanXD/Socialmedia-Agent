export type NavItem = { href: string; number: string; label: string; hint: string };

export const NAV_ITEMS: readonly NavItem[] = [
  { href: "/mediathek", number: "01", label: "Mediathek", hint: "Clips und Fotos" },
  { href: "/highlights", number: "02", label: "Szenen und Highlights", hint: "Beste Momente" },
  { href: "/auftraege", number: "03", label: "Aufträge", hint: "Verarbeitung" },
  { href: "/freigabe", number: "04", label: "Freigabe und Export", hint: "Prüfen und exportieren" },
];

export function isActiveRoute(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function creatorLabel(displayName: string | null | undefined, email: string): string {
  const name = displayName?.trim();
  return name ? name : email;
}
