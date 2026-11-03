"use client";

import { usePathname } from "next/navigation";
import { NavLinks } from "./nav-links";

export function Navigation() {
  return (
    <nav aria-label="Hauptnavigation">
      <NavLinks pathname={usePathname()} />
    </nav>
  );
}
