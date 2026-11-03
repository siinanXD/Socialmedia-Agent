import { EmptyState } from "../../../components/studio/EmptyState";

export const metadata = { title: "Aufträge – Socialmedia-Agent" };

export default function Page() {
  return (
    <EmptyState number="03" title="Aufträge" status="Geplant">
      Noch keine Daten: Verarbeitungsaufträge und ihr Status erscheinen hier.
    </EmptyState>
  );
}
