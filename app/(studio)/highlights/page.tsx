import { EmptyState } from "../../../components/studio/EmptyState";

export const metadata = { title: "Szenen und Highlights – Socialmedia-Agent" };

export default function Page() {
  return (
    <EmptyState number="02" title="Szenen und Highlights" status="Geplant">
      Noch keine Daten: Erkannte Szenen und Highlights deiner Clips erscheinen hier, sobald die Analyse gebaut ist.
    </EmptyState>
  );
}
