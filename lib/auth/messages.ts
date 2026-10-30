const MESSAGES: Record<string, string> = {
  eingabe: "Bitte E-Mail und Passwort eingeben.",
  passwort: "Das Passwort muss mindestens 8 Zeichen lang sein.",
  anmeldung: "Anmeldung fehlgeschlagen. Bitte E-Mail und Passwort prüfen.",
  registrierung: "Registrierung nicht möglich. Bitte die Angaben prüfen oder anmelden.",
  bestaetigen: "Bitte die E-Mail-Adresse über den zugesandten Link bestätigen, dann anmelden.",
};

/** Feste Texte nach Code. Unbekannte Codes (z. B. aus der URL) ergeben nichts; Rohmeldungen von Supabase kommen nie bis hierher. */
export function messageFor(code: string | string[] | undefined): string | null {
  if (typeof code !== "string") return null;
  return Object.hasOwn(MESSAGES, code) ? MESSAGES[code] : null;
}
