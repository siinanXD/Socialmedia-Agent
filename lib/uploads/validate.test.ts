import { describe, expect, it } from "vitest";
import { MAX_UPLOAD_BYTES, objectPath, parseUploadRequest, safeFilename } from "./validate";

const OK = {
  filename: "training.mp4",
  mimeType: "video/mp4",
  sizeBytes: 1000,
  sha256: "a".repeat(64),
  rights: { source: "own", statement: "Selbst gefilmt." },
};

describe("parseUploadRequest", () => {
  it("nimmt eine gültige Anfrage an", () => {
    expect(parseUploadRequest(OK)).toEqual({ ok: true, value: OK });
  });

  it.each([
    ["falscher MIME", { ...OK, mimeType: "application/pdf" }, "typ"],
    ["501 MB", { ...OK, sizeBytes: 501 * 1024 * 1024 }, "groesse"],
    ["leere Datei", { ...OK, sizeBytes: 0 }, "groesse"],
    ["fehlende Rechte", { ...OK, rights: undefined }, "rechte"],
    ["leere Erklärung", { ...OK, rights: { source: "own", statement: "  " } }, "rechte"],
    ["unbekannte Quelle", { ...OK, rights: { source: "gefunden", statement: "x" } }, "rechte"],
    ["kein Hash", { ...OK, sha256: "xyz" }, "ungueltig"],
    ["kein Objekt", null, "ungueltig"],
  ])("lehnt ab: %s", (_name, body, code) => {
    expect(parseUploadRequest(body)).toEqual({ ok: false, code });
  });

  it("erlaubt genau 500 MB", () => {
    expect(parseUploadRequest({ ...OK, sizeBytes: MAX_UPLOAD_BYTES }).ok).toBe(true);
  });
});

describe("safeFilename und objectPath", () => {
  it("entfernt Pfadtricks und Sonderzeichen", () => {
    expect(safeFilename("../../etc/passwd")).toBe("passwd");
    expect(safeFilename("..\\..\\boot.ini")).toBe("boot.ini");
    expect(safeFilename("Mein Clip (1).mp4")).toBe("Mein_Clip_1_.mp4");
    expect(safeFilename("..")).toBe("datei");
    expect(safeFilename("")).toBe("datei");
  });

  it("baut den Pfad nur aus Creator, Asset und bereinigtem Namen", () => {
    expect(objectPath("c1", "a1", "../x/clip.mp4")).toBe("originals/c1/a1/clip.mp4");
  });
});
