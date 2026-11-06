"""Transkript-Schnittstelle und Untertitel-Dateien für 9:16 (SIN-1356).

Nur Schnittstelle und Ausgabe; die Spracherkennung folgt hinter ``Transcriber`` (SIN-1357).
Untertitel: höchstens 32 Zeichen je Zeile und 2 Zeilen je Cue; längere Segmente werden geteilt und
ihre Zeit nach Zeichenzahl aufgeteilt. Cues überlappen nie.
"""

from __future__ import annotations

import textwrap
from collections.abc import Iterator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol

MAX_CHARS = 32
MAX_LINES = 2


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str
    confidence: float | None = None


@dataclass(frozen=True)
class Transcript:
    language: str
    segments: tuple[TranscriptSegment, ...] = ()


class Transcriber(Protocol):
    def transcribe(self, path: Path, language: str) -> Transcript: ...


class FakeTranscriber:
    """Liefert ein festes Transkript; für Tests ohne Spracherkennung."""

    def __init__(self, transcript: Transcript) -> None:
        self.transcript = transcript

    def transcribe(self, path: Path, language: str) -> Transcript:
        return self.transcript


def clip(transcript: Transcript, start: float, end: float) -> Transcript:
    """Schneidet den Bereich ``[start, end)`` aus und verschiebt die Zeiten auf 0."""
    segments = tuple(
        replace(s, start=max(s.start, start) - start, end=min(s.end, end) - start)
        for s in transcript.segments
        if s.start < end and s.end > start
    )
    return Transcript(transcript.language, segments)


def _cues(transcript: Transcript) -> Iterator[tuple[float, float, list[str]]]:
    previous_end = 0.0
    for seg in sorted(transcript.segments, key=lambda s: (s.start, s.end)):
        lines = textwrap.wrap(seg.text, MAX_CHARS, break_long_words=True)
        start = max(seg.start, previous_end)
        if not lines or seg.end <= start:
            continue
        chunks = [lines[i : i + MAX_LINES] for i in range(0, len(lines), MAX_LINES)]
        total = sum(len(line) for line in lines)
        done = 0
        for chunk in chunks:
            cue_start = start + (seg.end - start) * done / total
            done += sum(len(line) for line in chunk)
            cue_end = start + (seg.end - start) * done / total
            yield cue_start, cue_end, chunk
        previous_end = seg.end


def _timestamp(seconds: float, separator: str) -> str:
    ms = round(seconds * 1000)
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{ms:03d}"


def write_srt(transcript: Transcript, path: Path) -> None:
    blocks = [
        f"{n}\n{_timestamp(a, ',')} --> {_timestamp(b, ',')}\n" + "\n".join(lines) + "\n"
        for n, (a, b, lines) in enumerate(_cues(transcript), start=1)
    ]
    path.write_text("\n".join(blocks), encoding="utf-8", newline="\n")


def write_vtt(transcript: Transcript, path: Path) -> None:
    blocks = [
        f"{_timestamp(a, '.')} --> {_timestamp(b, '.')}\n" + "\n".join(lines) + "\n"
        for a, b, lines in _cues(transcript)
    ]
    path.write_text("\n".join(["WEBVTT\n", *blocks]), encoding="utf-8", newline="\n")
