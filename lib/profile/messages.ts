const ERRORS: Record<string, string> = {
  nische: "Die Nische darf höchstens 100 Zeichen lang sein.",
  tonalitaet: "Die Tonalität darf höchstens 500 Zeichen lang sein.",
  zielgruppe: "Die Zielgruppe darf höchstens 500 Zeichen lang sein.",
  plattform: "Diese Plattform wird nicht unterstützt. Bitte nur YouTube, Instagram oder TikTok wählen.",
  quelle: "Diese Quelle ist nicht erlaubt. Bitte nur die angebotenen Quellen wählen.",
  hashtags_anzahl: "Bitte höchstens 30 Hashtags angeben.",
  hashtags_zeichen: "Hashtags dürfen nur Buchstaben, Ziffern und Unterstriche enthalten (höchstens 50 Zeichen).",
  speichern: "Das Profil konnte nicht gespeichert werden. Bitte später noch einmal versuchen.",
  laden: "Das Profil konnte gerade nicht geladen werden. Bitte später noch einmal versuchen.",
};

const NOTICES: Record<string, string> = {
  gespeichert: "Profil gespeichert.",
};

export type ProfileMessage = { kind: "ok" | "error"; text: string };

/** Feste Texte nach Code aus der URL; unbekannte Codes ergeben nichts. */
export function profileMessage(params: { fehler?: string | string[]; hinweis?: string | string[] }): ProfileMessage | null {
  const { fehler, hinweis } = params;
  if (typeof fehler === "string" && Object.hasOwn(ERRORS, fehler)) return { kind: "error", text: ERRORS[fehler] };
  if (typeof hinweis === "string" && Object.hasOwn(NOTICES, hinweis)) return { kind: "ok", text: NOTICES[hinweis] };
  return null;
}
