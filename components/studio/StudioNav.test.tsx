import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { StudioNavList } from "./StudioNav";

describe("StudioNavList", () => {
  it("markiert nur die aktive Route mit aria-current", () => {
    const html = renderToStaticMarkup(<StudioNavList pathname="/auftraege" />);
    expect(html.match(/aria-current="page"/g)).toHaveLength(1);
    const linkTo = (href: string) => html.match(new RegExp(`<a [^>]*href="${href}"[^>]*>`))?.[0] ?? "";
    expect(linkTo("/auftraege")).toContain('aria-current="page"');
    expect(linkTo("/mediathek")).not.toContain("aria-current");
  });
  it("beschriftet alle vier Bereiche auf Deutsch", () => {
    const html = renderToStaticMarkup(<StudioNavList pathname="/" />);
    for (const label of ["Mediathek", "Szenen und Highlights", "Aufträge", "Freigabe und Export"]) {
      expect(html).toContain(label);
    }
    expect(html).not.toContain("aria-current");
  });
});
