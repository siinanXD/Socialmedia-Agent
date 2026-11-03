import { redirect } from "next/navigation";

// Nicht angemeldete Besucher fängt proxy.ts ab; das Studio-Layout prüft zusätzlich.
export default function Home() {
  redirect("/mediathek");
}
