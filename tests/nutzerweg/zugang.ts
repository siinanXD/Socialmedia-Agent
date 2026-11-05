export type Zugang = { liveUrl: string; email: string; passwort: string };

/** Liest LIVE_URL, TESTNUTZER_EMAIL, TESTNUTZER_PASSWORT; nennt fehlende Namen, nie Werte. */
export function zugangAus(env: Record<string, string | undefined>): Zugang {
  const fehlend = ["LIVE_URL", "TESTNUTZER_EMAIL", "TESTNUTZER_PASSWORT"].filter((name) => !env[name]);
  if (fehlend.length > 0) throw new Error(`Fehlende Umgebungsvariablen: ${fehlend.join(", ")}`);
  return { liveUrl: env.LIVE_URL!, email: env.TESTNUTZER_EMAIL!, passwort: env.TESTNUTZER_PASSWORT! };
}
