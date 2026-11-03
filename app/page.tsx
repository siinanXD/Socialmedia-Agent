import { redirect } from "next/navigation";

// Nicht angemeldet fängt proxy.ts ab (→ /login); angemeldet geht es in die Mediathek.
export default function Home() {
  redirect("/mediathek");
}
