import { defineConfig } from "@playwright/test";

// Nutzerweg (SIN-1460): spielt die gebauten Wege wie ein Mensch durch, gegen LIVE_URL.
// Format wie die Figma-Vorlage 0zcOlwmRdnmKoTJPneNwgC: Desktop 1440x900, dunkel.
export default defineConfig({
  testDir: "tests/nutzerweg",
  testMatch: "**/*.nutzerweg.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  // Die Live-Adresse startet kalt und leitet nach dem Login zweimal weiter.
  expect: { timeout: 15_000 },
  outputDir: "test-results/nutzerweg",
  reporter: [["./tests/nutzerweg/reporter.ts"]],
  use: {
    baseURL: process.env.LIVE_URL,
    viewport: { width: 1440, height: 900 },
    colorScheme: "dark",
    locale: "de-DE",
  },
});
