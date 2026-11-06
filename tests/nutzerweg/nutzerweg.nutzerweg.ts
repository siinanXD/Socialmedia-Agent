import { expect, test, type Page } from "@playwright/test";
import { resolve } from "node:path";
import { zweitesKontoAus, zugangAus } from "./zugang";

const zugang = zugangAus(process.env);

// Ein Mensch, ein Durchgang: die Wege laufen der Reihe nach.
test.describe.configure({ mode: "serial" });

async function shot(page: Page, name: string) {
  await page.screenshot({ path: `test-results/nutzerweg/${name}.png`, fullPage: true });
}

async function anmelden(page: Page, konto: { email: string; passwort: string } = zugang) {
  await page.goto("/login");
  await page.getByLabel("E-Mail").fill(konto.email);
  await page.getByLabel("Passwort").fill(konto.passwort);
  await page.getByRole("button", { name: "Anmelden" }).click();
  await expect(page.getByRole("heading", { name: "Mediathek", level: 1 })).toBeVisible();
  // SIN-1582: Die Adresszeile zeigt die Seite, nicht "/", und die Navigation markiert sie.
  await expect(page).toHaveURL(/\/mediathek$/);
  await expect(page.getByRole("navigation", { name: "Hauptnavigation" }).getByRole("link", { name: "Mediathek" })).toHaveAttribute("aria-current", "page");
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
  await expect(page.getByRole("banner").getByText(zugang.email)).toBeVisible();
  await shot(page, "02-anmelden");
});

test("Creator vorhanden", async ({ page }) => {
  // Das Studio-Layout legt den Creator an (ensureCreator) und bricht ohne ihn mit einem Fehler ab.
  await anmelden(page);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Mediathek", level: 1 })).toBeVisible();
  await expect(page.getByText(/Application error|Internal Server Error/i)).toHaveCount(0);
  await shot(page, "03-creator");
});

test("Vier Bereiche in der Navigation", async ({ page }) => {
  await anmelden(page);
  const navigation = page.getByRole("navigation", { name: "Hauptnavigation" });
  for (const bereich of ["Mediathek", "Highlights", "Aufträge", "Freigabe & Export"]) {
    await navigation.getByRole("link", { name: bereich }).click();
    await expect(page.getByRole("heading", { name: bereich, level: 1 })).toBeVisible();
    await expect(navigation.getByRole("link", { name: bereich })).toHaveAttribute("aria-current", "page");
  }
  await shot(page, "04-bereiche");
});

test("Handy: Mediathek nach dem Anmelden", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await anmelden(page);
  await shot(page, "05-handy-mediathek");
});

test("Abmelden", async ({ page }) => {
  await anmelden(page);
  await page.getByRole("button", { name: "Abmelden" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await shot(page, "06-abmelden");
});

test("Ohne Sitzung leitet / auf /login weiter", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Anmelden" })).toBeVisible();
  await shot(page, "07-weiterleitung");
});

// SIN-1387: echter Clip (2 s, 216x384, H.264/AAC, mit FFmpeg aus testsrc erzeugt, keine fremden Inhalte).
const CLIP = resolve("tests/nutzerweg/nutzerweg-testclip.mp4");

test("Material hochladen und nach dem Neuladen wiedersehen", async ({ page }) => {
  await anmelden(page);
  await page.locator('input[type="file"]').setInputFiles(CLIP);
  await page.getByRole("textbox", { name: /^Rechte-Bestätigung/ }).fill("Testclip, selbst erzeugt.");
  await page.getByRole("button", { name: "Hochladen" }).click();
  // Beim wiederholten Lauf liegt der Clip schon da; beides heißt: er gehört diesem Konto.
  await expect(page.getByText(/ist hochgeladen und wird geprüft|liegt schon in deiner Mediathek/)).toBeVisible();
  await page.reload();
  await expect(page.getByRole("list").getByText("nutzerweg-testclip.mp4")).toBeVisible();
  await shot(page, "08-hochgeladen");
});

test("Zweites Konto sieht den Clip nicht", async ({ page }) => {
  await anmelden(page, zweitesKontoAus(process.env));
  await expect(page.getByText("nutzerweg-testclip.mp4")).toHaveCount(0);
  await shot(page, "09-zweites-konto");
});

// Noch nicht gebaut: wird gelistet, nie grün. Wer einen Weg baut, ersetzt den Eintrag durch einen echten Test.
const nochNichtGebaut = [
  "Highlights ansehen",
  "Post-Entwurf prüfen und freigeben",
  "Veröffentlichen",
];
for (const weg of nochNichtGebaut) {
  test(`[noch nicht gebaut] ${weg}`, () => {
    test.skip(true, "noch nicht gebaut");
  });
}
