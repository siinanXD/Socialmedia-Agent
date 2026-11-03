import { EmptyState } from "../../../components/studio/EmptyState";

export const metadata = { title: "Mediathek – Socialmedia-Agent" };

export default function Page() {
  return (
    <EmptyState number="01" title="Mediathek" status="Geplant">
      Noch keine Daten: Hier erscheinen deine hochgeladenen Clips und Fotos. Der Upload ist noch nicht gebaut.
    </EmptyState>
  );
}
