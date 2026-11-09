"""Lange Dateien in Chunks analysieren (SIN-1365).

ffmpeg dekodiert je Aufruf nur einen Chunk (``-ss``/``-t`` vor ``-i``); Python sieht nur die
gemeldeten Schnitte. Der Speicherbedarf hängt deshalb nicht von der Dateilänge ab.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from socialmedia_worker.highlights import select_highlights
from socialmedia_worker.pipeline import (
    MAX_LEN,
    MIN_LEN,
    PIPELINE_VERSION,
    AnalysisResult,
    in_fenster,
)
from socialmedia_worker.scenes import SceneCut, detect_scenes, to_segments
from socialmedia_worker.signals import segment_signals
from socialmedia_worker.validate import MediaLimits, MediaRejectedError, validate_media

CHUNK_S = 600.0
OVERLAP_S = 5.0
# Mehr als die 30 Minuten aus MediaLimits gibt es nur auf diesem Weg.
CHUNKED_LIMITS = MediaLimits(max_duration=3 * 3600)
# Ein Schnitt in der Überlappung wird von zwei Chunks gemeldet; näher als das ist derselbe.
SAME_CUT_S = 0.1

Progress = Callable[[int, int], None]  # (fertige Chunks, alle Chunks)


def plan_chunks(
    duration: float, chunk_s: float = CHUNK_S, overlap_s: float = OVERLAP_S
) -> list[tuple[float, float]]:
    """(start, end) je Chunk; jeder beginnt `overlap_s` vor dem Ende des vorigen."""
    if duration <= 0 or not 0 <= overlap_s < chunk_s:
        raise ValueError("need duration > 0 and 0 <= overlap_s < chunk_s")
    chunks: list[tuple[float, float]] = []
    start = 0.0
    while True:
        end = min(start + chunk_s, duration)
        chunks.append((start, end))
        if end >= duration:
            return chunks
        start = end - overlap_s


def detect_scenes_chunked(
    path: Path,
    duration: float,
    chunk_s: float = CHUNK_S,
    overlap_s: float = OVERLAP_S,
    threshold: float = 0.3,
    limits: MediaLimits = CHUNKED_LIMITS,
    on_progress: Progress | None = None,
) -> list[SceneCut]:
    """Wie detect_scenes, aber Chunk für Chunk; Zeiten absolut, Überlappung ohne Doppelte."""
    chunks = plan_chunks(duration, chunk_s, overlap_s)
    cuts: list[SceneCut] = []
    for i, (start, end) in enumerate(chunks, start=1):
        for cut in detect_scenes(path, threshold, start=start, length=end - start, limits=limits):
            if not cuts or cut.time - cuts[-1].time > SAME_CUT_S:
                cuts.append(cut)
        if on_progress is not None:
            on_progress(i, len(chunks))
    return cuts


def analyze_chunked(
    path: Path,
    asset_id: str,
    limits: MediaLimits = CHUNKED_LIMITS,
    top_n: int = 3,
    chunk_s: float = CHUNK_S,
    overlap_s: float = OVERLAP_S,
    on_progress: Progress | None = None,
) -> AnalysisResult:
    """analyze_asset für ein Video bis 3 h (Standard): Szenen je Chunk, Rest wie gehabt."""
    media = validate_media(path, limits)
    if media.kind != "video" or media.duration is None:
        raise MediaRejectedError("unsupported_format", f"{path.name}: not a video")
    cuts = detect_scenes_chunked(
        path, media.duration, chunk_s, overlap_s, limits=limits, on_progress=on_progress
    )
    segments = in_fenster(to_segments(cuts, media.duration))
    signals = [s.motion for s in segment_signals(path, segments, limits)]
    manifest = select_highlights(
        asset_id, segments, signals, MIN_LEN, min(MAX_LEN, media.duration), top_n
    )
    return AnalysisResult(
        asset_id,
        "video",
        media.sha256,
        media.duration,
        media.width,
        media.height,
        segments,
        manifest.highlights,
        None,
        PIPELINE_VERSION,
    )
