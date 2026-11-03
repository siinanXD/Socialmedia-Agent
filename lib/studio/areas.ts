export type Area = {
  nr: string;
  href: string;
  label: string;
  /** Ehrlicher Leerzustand: was der Bereich tun soll und dass es ihn noch nicht gibt. */
  empty: { title: string; text: string };
};

export const AREAS: readonly Area[] = [
  {
    nr: "01",
    href: "/mediathek",
    label: "Mediathek",
    empty: {
      title: "Noch keine Daten",
      text: "Hier erscheinen deine hochgeladenen Clips und Fotos. Der Upload ist geplant.",
    },
  },
  {
    nr: "02",
    href: "/highlights",
    label: "Szenen und Highlights",
    empty: {
      title: "Noch keine Daten",
      text: "Hier erscheinen erkannte Szenen und Highlights deiner Clips. Die Erkennung ist geplant.",
    },
  },
  {
    nr: "03",
    href: "/auftraege",
    label: "Aufträge",
    empty: {
      title: "Noch keine Daten",
      text: "Hier erscheinen Schnitt- und Exportaufträge mit ihrem Status. Geplant.",
    },
  },
  {
    nr: "04",
    href: "/freigabe",
    label: "Freigabe und Export",
    empty: {
      title: "Noch keine Daten",
      text: "Hier prüfst und gibst du fertige Posts frei. Es wird nichts ohne deine Freigabe veröffentlicht. Geplant.",
    },
  },
];

/** Aktiv ist die Route selbst und jede Unterseite, aber kein bloßer Präfix-Treffer. */
export function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}
