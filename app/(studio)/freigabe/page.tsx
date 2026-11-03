import { EmptyState } from "../../../components/studio/EmptyState";

export const metadata = { title: "Freigabe und Export – Socialmedia-Agent" };

export default function Page() {
  return (
    <EmptyState number="04" title="Freigabe und Export" status="Geplant">
      Noch keine Daten: Fertige Posts prüfst du hier und gibst sie frei. Es wird nichts ohne deine Freigabe veröffentlicht.
    </EmptyState>
  );
}
