export type Section = {
  href: string;
  label: string;
  leer: { titel: string; text: string };
};

export const SECTIONS: readonly Section[] = [
  {
    href: "/mediathek",
    label: "Mediathek",
    leer: { titel: "Noch keine Medien", text: "Geplant: Hier erscheinen deine hochgeladenen Clips und Fotos." },
  },
  {
    href: "/highlights",
    label: "Highlights",
    leer: { titel: "Noch keine Daten", text: "Geplant: Erkannte Szenen und Highlights deiner Medien." },
  },
  {
    href: "/auftraege",
    label: "Aufträge",
    leer: { titel: "Noch keine Aufträge", text: "Geplant: Laufende und fertige Schnitt-Aufträge." },
  },
  {
    href: "/freigabe",
    label: "Freigabe & Export",
    leer: {
      titel: "Nichts zur Freigabe",
      text: "Geplant: Varianten prüfen, freigeben und exportieren. Veröffentlicht wird nie automatisch.",
    },
  },
];

export function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(href + "/");
}
