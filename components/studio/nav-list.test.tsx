import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { NavList } from "./nav-list";

describe("NavList", () => {
  it("markiert nur die aktive Route mit aria-current", () => {
    const html = renderToStaticMarkup(<NavList pathname="/auftraege" />);
    expect(html.match(/aria-current="page"/g)).toHaveLength(1);
    expect(html).toMatch(/href="\/auftraege"[^>]*aria-current="page"/);
    expect(html).not.toMatch(/href="\/mediathek"[^>]*aria-current/);
  });
  it("hat deutsche Beschriftungen und eine Navigationsmarke", () => {
    const html = renderToStaticMarkup(<NavList pathname="/" />);
    expect(html).toContain('aria-label="Hauptnavigation"');
    expect(html).toContain("Freigabe und Export");
    expect(html).not.toContain("aria-current");
  });
});
