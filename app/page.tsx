import { redirect } from "next/navigation";

// Die Anmeldeprüfung übernimmt das Studio-Layout von /mediathek (und proxy.ts).
export default function Home() {
  redirect("/mediathek");
}
