import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const status = vi.hoisted(() => ({ pending: false }));
vi.mock("react-dom", async (orig) => ({ ...(await orig<typeof import("react-dom")>()), useFormStatus: () => ({ pending: status.pending }) }));

import { SubmitButton } from "./submit-button";

describe("SubmitButton", () => {
  beforeEach(() => {
    status.pending = false;
  });

  it("ist im Ruhezustand klickbar und zeigt die Beschriftung", () => {
    const html = renderToStaticMarkup(<SubmitButton label="Anmelden" pendingLabel="Anmeldung läuft …" />);
    expect(html).toContain("Anmelden");
    expect(html).not.toContain("disabled");
    expect(html).not.toContain("Anmeldung läuft");
  });

  it("zeigt beim Warten eine Ladeanzeige und sperrt den Knopf gegen Doppelklick", () => {
    status.pending = true;
    const html = renderToStaticMarkup(<SubmitButton label="Anmelden" pendingLabel="Anmeldung läuft …" />);
    expect(html).toContain("disabled");
    expect(html).toContain('aria-busy="true"');
    expect(html).toContain("Anmeldung läuft …");
    expect(html).toContain('class="spinner"');
  });
});
