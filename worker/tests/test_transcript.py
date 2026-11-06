"""SIN-1356: Transkript-Schnittstelle, SRT/VTT für 9:16 und clip()."""

from pathlib import Path

from socialmedia_worker.transcript import (
    FakeTranscriber,
    Transcript,
    TranscriptSegment,
    clip,
    write_srt,
    write_vtt,
)

KURZ = TranscriptSegment(0.0, 1.5, "Hallo zusammen!", 0.9)
LANG = TranscriptSegment(
    2.0,
    6.0,
    "Heute zeige ich euch drei Übungen für einen starken Rücken, ganz ohne Geräte.",
)
T = Transcript("de", (KURZ, LANG))


def test_fake_transcriber_liefert_vorgabe(tmp_path: Path) -> None:
    assert FakeTranscriber(T).transcribe(tmp_path / "clip.mp4", "de") == T


def test_srt_gegen_erwartete_datei(tmp_path: Path) -> None:
    ziel = tmp_path / "clip.srt"
    write_srt(T, ziel)
    assert ziel.read_bytes().decode("utf-8") == (
        "1\n00:00:00,000 --> 00:00:01,500\nHallo zusammen!\n\n"
        "2\n00:00:02,000 --> 00:00:04,667\nHeute zeige ich euch drei\nÜbungen für einen starken\n\n"
        "3\n00:00:04,667 --> 00:00:06,000\nRücken, ganz ohne Geräte.\n"
    )


def test_vtt_gegen_erwartete_datei(tmp_path: Path) -> None:
    ziel = tmp_path / "clip.vtt"
    write_vtt(T, ziel)
    assert ziel.read_text(encoding="utf-8") == (
        "WEBVTT\n\n"
        "00:00:00.000 --> 00:00:01.500\nHallo zusammen!\n\n"
        "00:00:02.000 --> 00:00:04.667\nHeute zeige ich euch drei\nÜbungen für einen starken\n\n"
        "00:00:04.667 --> 00:00:06.000\nRücken, ganz ohne Geräte.\n"
    )


def test_zeilen_hoechstens_32_zeichen_und_2_zeilen(tmp_path: Path) -> None:
    wort = "Rückenstrecker" * 4  # 56 Zeichen ohne Leerzeichen
    ziel = tmp_path / "x.srt"
    write_srt(Transcript("de", (TranscriptSegment(0, 3, f"{wort} {LANG.text}"),)), ziel)
    bloecke = ziel.read_text(encoding="utf-8").strip().split("\n\n")
    for block in bloecke:
        zeilen = block.split("\n")[2:]
        assert 1 <= len(zeilen) <= 2
        assert all(len(z) <= 32 for z in zeilen)


def test_keine_ueberlappung_und_stunden(tmp_path: Path) -> None:
    ueberlappend = Transcript(
        "de",
        (
            TranscriptSegment(3661.0, 3663.0, "später"),
            TranscriptSegment(3660.0, 3662.0, "früher"),
        ),
    )
    ziel = tmp_path / "x.srt"
    write_srt(ueberlappend, ziel)
    assert ziel.read_text(encoding="utf-8") == (
        "1\n01:01:00,000 --> 01:01:02,000\nfrüher\n\n2\n01:01:02,000 --> 01:01:03,000\nspäter\n"
    )


def test_leeres_transkript(tmp_path: Path) -> None:
    leer = Transcript("de", ())
    write_srt(leer, tmp_path / "x.srt")
    write_vtt(leer, tmp_path / "x.vtt")
    assert (tmp_path / "x.srt").read_text(encoding="utf-8") == ""
    assert (tmp_path / "x.vtt").read_text(encoding="utf-8") == "WEBVTT\n"


def test_leere_und_stumme_segmente_fallen_weg(tmp_path: Path) -> None:
    t = Transcript("de", (TranscriptSegment(0, 1, "   "), TranscriptSegment(2, 2, "null"), KURZ))
    write_srt(t, tmp_path / "x.srt")
    assert (
        (tmp_path / "x.srt")
        .read_text(encoding="utf-8")
        .startswith("1\n00:00:00,000 --> 00:00:01,500")
    )


def test_clip_verschiebt_auf_null() -> None:
    assert clip(T, 2.0, 6.0) == Transcript("de", (TranscriptSegment(0.0, 4.0, LANG.text, None),))


def test_clip_schneidet_halbe_segmente() -> None:
    ergebnis = clip(T, 1.0, 3.0)
    assert ergebnis.segments == (
        TranscriptSegment(0.0, 0.5, "Hallo zusammen!", 0.9),
        TranscriptSegment(1.0, 2.0, LANG.text, None),
    )


def test_clip_ohne_treffer_ist_leer() -> None:
    assert clip(T, 1.5, 2.0) == Transcript("de", ())
    assert clip(T, 10.0, 12.0).segments == ()
