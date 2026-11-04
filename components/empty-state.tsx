import { SECTIONS } from "../lib/studio/sections";

export function SectionPage({ href }: { href: string }) {
  const s = SECTIONS.find((x) => x.href === href);
  if (!s) throw new Error("Unbekannter Bereich: " + href);
  return (
    <>
      <h1>{s.label}</h1>
      <section className="empty" aria-labelledby="leer-titel">
        <h2 id="leer-titel">{s.leer.titel}</h2>
        <p>{s.leer.text}</p>
      </section>
    </>
  );
}
