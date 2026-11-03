import type { Area } from "../../lib/studio/areas";

export function AreaPage({ area }: { area: Area }) {
  return (
    <section aria-labelledby="bereich-titel">
      <p className="area-nr">Bereich {area.nr}</p>
      <h1 id="bereich-titel">{area.label}</h1>
      <div className="empty">
        <h2>{area.empty.title}</h2>
        <p>{area.empty.text}</p>
      </div>
    </section>
  );
}
