import { redirect } from "next/navigation";

// Nicht angemeldete Nutzer fängt proxy.ts bzw. das Studio-Layout ab.
export default function Home() {
  redirect("/mediathek");
}
