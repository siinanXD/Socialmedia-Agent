export type Section = {
  href: string;
  nummer: string;
  label: string;
  beschreibung: string;
};

export const SECTIONS: readonly Section[] = [
  { href: "/mediathek", nummer: "01", label: "Mediathek", beschreibung: "Hochgeladene Clips und Fotos." },
  { href: "/highlights", nummer: "02", label: "Szenen und Highlights", beschreibung: "Erkannte Szenen und Highlights." },
  { href: "/auftraege", nummer: "03", label: "Aufträge", beschreibung: "Laufende und abgeschlossene Aufträge." },
  { href: "/freigabe", nummer: "04", label: "Freigabe und Export", beschreibung: "Prüfen, freigeben und exportieren." },
];

export function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}
