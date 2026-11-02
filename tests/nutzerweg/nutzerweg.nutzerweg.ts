import { expect, test, type Page } from "@playwright/test";
import { zugangAus } from "./zugang";

const zugang = zugangAus(process.env);

// Ein Mensch, ein Durchgang: die Wege laufen der Reihe nach.
test.describe.configure({ mode: "serial" });

async function shot(page: Page, name: string) {
  await page.screenshot({ path: `test-results/nutzerweg/${name}.png`, fullPage: true });
}

async function anmelden(page: Page) {
  await page.goto("/login");
  await page.getByLabel("E-Mail").fill(zugang.email);
  await page.getByLabel("Passwort").fill(zugang.passwort);
  await page.getByRole("button", { name: "Anmelden" }).click();
  await expect(page.getByRole("heading", { name: "Socialmedia-Agent" })).toBeVisible();
}

test("Registrierungsseite ist erreichbar", async ({ page }) => {
  await page.goto("/registrieren");
  await expect(page.getByRole("heading", { name: "Registrieren" })).toBeVisible();
  await expect(page.getByLabel("E-Mail")).toBeVisible();
  await expect(page.getByLabel(/Passwort/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Registrieren" })).toBeVisible();
  await shot(page, "01-registrieren");
});

test("Anmelden mit dem Testkonto", async ({ page }) => {
  await anmelden(page);
  await expect(page.getByText(`Angemeldet als ${zugang.email}`)).toBeVisible();
  await shot(page, "02-anmelden");
});

test("Creator vorhanden", async ({ page }) => {
  // Die Startseite legt den Creator an (ensureCreator) und bricht ohne ihn mit einem Fehler ab.
  await anmelden(page);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Socialmedia-Agent" })).toBeVisible();
  await expect(page.getByText(/Application error|Internal Server Error/i)).toHaveCount(0);
  await shot(page, "03-creator");
});

test("Abmelden", async ({ page }) => {
  await anmelden(page);
  await page.getByRole("button", { name: "Abmelden" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await shot(page, "04-abmelden");
});

test("Ohne Sitzung leitet / auf /login weiter", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Anmelden" })).toBeVisible();
  await shot(page, "05-weiterleitung");
});

// Noch nicht gebaut: wird gelistet, nie grün. Wer einen Weg baut, ersetzt den Eintrag durch einen echten Test.
const nochNichtGebaut = [
  "Material hochladen (Videos und Fotos)",
  "Highlights ansehen",
  "Post-Entwurf prüfen und freigeben",
  "Veröffentlichen",
];
for (const weg of nochNichtGebaut) {
  test(`[noch nicht gebaut] ${weg}`, () => {
    test.skip(true, "noch nicht gebaut");
  });
}
