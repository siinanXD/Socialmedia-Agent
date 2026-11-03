import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { NavLinks } from "./nav-links";

describe("NavLinks", () => {
  it("setzt aria-current nur auf den aktiven Bereich", () => {
    const html = renderToStaticMarkup(<NavLinks pathname="/auftraege" />);
    expect(html.match(/aria-current="page"/g)).toHaveLength(1);
    const active = html.match(/<a [^>]*aria-current="page"[^>]*>/)?.[0] ?? "";
    expect(active).toContain('href="/auftraege"');
    expect(html).toContain("Freigabe und Export");
  });
});
