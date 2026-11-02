"use client";

import { usePathname } from "next/navigation";
import { NavList } from "./nav-list";

export function Nav() {
  return <NavList pathname={usePathname()} />;
}
