import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "Socialmedia-Agent",
  description: "Planungsstand: noch keine Funktion.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="de">
      <body>{children}</body>
    </html>
  );
}
