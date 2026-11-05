import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("../lib/auth/actions", () => ({ loginAction: vi.fn(), registerAction: vi.fn() }));

import LoginPage from "../app/login/page";
import RegisterPage from "../app/registrieren/page";

const render = async (page: (p: { searchParams: Promise<Record<string, string>> }) => Promise<React.ReactElement>) =>
  renderToStaticMarkup(await page({ searchParams: Promise.resolve({}) }));

describe("Einleitung auf Anmeldung und Registrierung", () => {
  it.each([
    ["/login", LoginPage],
    ["/registrieren", RegisterPage],
  ])("%s sagt, was die App ist und was nach der Anmeldung kommt", async (_pfad, page) => {
    const html = await render(page);
    expect(html).toContain("Creator-Studio");
    expect(html).toContain("Reels und Shorts im Hochformat");
    expect(html).toContain("Mediathek");
    expect(html).toContain("Veröffentlicht wird nichts automatisch");
  });
});
