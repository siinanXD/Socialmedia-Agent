import { SECTIONS } from "../../lib/studio/sections";

export function SectionPage({ href }: { href: string }) {
  const s = SECTIONS.find((x) => x.href === href);
  if (!s) throw new Error(`Unbekannter Bereich ${href}`);
  return (
    <section aria-labelledby="seitentitel">
      <p className="studio-kicker">Bereich {s.nummer}</p>
      <h1 id="seitentitel">{s.label}</h1>
      <p>{s.beschreibung}</p>
      <div className="studio-empty">
        <p><strong>Geplant</strong> – noch keine Daten.</p>
        <p>Dieser Bereich ist ein Rahmen; die Funktion folgt in einem späteren Schritt.</p>
      </div>
    </section>
  );
}
