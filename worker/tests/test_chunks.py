import json
import subprocess
from pathlib import Path

import pytest

from socialmedia_worker.chunks import (
    CHUNKED_LIMITS,
    analyze_chunked,
    detect_scenes_chunked,
    plan_chunks,
)
from socialmedia_worker.pipeline import analyze_asset, validate_analysis
from socialmedia_worker.scenes import detect_scenes
from socialmedia_worker.signals import segment_signals
from socialmedia_worker.validate import MediaLimits, MediaRejectedError

# Schnitte bei 10, 19, 37, 45 und 54,5 s. Bei Chunk 20 s / Überlappung 2 s liegen 19, 37 und
# 54,5 in einer Überlappung (18-20, 36-38, 54-56) und würden ohne Abgleich doppelt gemeldet.
PARTS = [
    ("testsrc", 10.0),
    ("color=c=red", 9.0),
    ("testsrc2", 18.0),
    ("color=c=blue", 8.0),
    ("smptebars", 9.5),
    ("color=c=green", 5.5),
]
CUTS = [10.0, 19.0, 37.0, 45.0, 54.5]


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", *args], check=True)


@pytest.fixture(scope="module")
def clip(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("chunks") / "sechzig.mp4"
    args: list[str] = []
    for source, seconds in PARTS:
        sep = ":" if "=" in source else "="
        args += ["-f", "lavfi", "-i", f"{source}{sep}duration={seconds}:size=320x240:rate=25"]
    graph = "".join(f"[{i}:v]" for i in range(len(PARTS)))
    _ffmpeg(*args, "-filter_complex", f"{graph}concat=n={len(PARTS)}:v=1:a=0,format=yuv420p",
            "-preset", "ultrafast", str(path))  # fmt: skip
    return path


@pytest.fixture(scope="module")
def long_clip(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """31 Minuten, 64x64, 1 Bild/s: über der 30-Minuten-Grenze und trotzdem schnell erzeugt."""
    path = tmp_path_factory.mktemp("lang") / "lang.mp4"
    _ffmpeg("-f", "lavfi", "-i", "color=c=black:duration=1860:size=64x64:rate=1",
            "-preset", "ultrafast", str(path))  # fmt: skip
    return path


def test_plan_chunks() -> None:
    assert plan_chunks(60.0, 20.0, 2.0) == [(0.0, 20.0), (18.0, 38.0), (36.0, 56.0), (54.0, 60.0)]
    assert plan_chunks(15.0, 20.0, 2.0) == [(0.0, 15.0)]  # Dauer < Chunk
    assert plan_chunks(20.0, 20.0, 2.0) == [(0.0, 20.0)]  # genau ein Chunk, kein leerer Rest
    assert plan_chunks(21.0, 20.0, 2.0) == [(0.0, 20.0), (18.0, 21.0)]  # Rest-Chunk
    assert plan_chunks(1860.0) == [
        (0.0, 600.0), (595.0, 1195.0), (1190.0, 1790.0), (1785.0, 1860.0),
    ]
    for duration, chunk_s, overlap_s in ((0.0, 20.0, 2.0), (60.0, 2.0, 2.0), (60.0, 20.0, -1.0)):
        with pytest.raises(ValueError):
            plan_chunks(duration, chunk_s, overlap_s)


def test_chunked_cuts_match_unchunked_without_doubles(clip: Path) -> None:
    whole = [c.time for c in detect_scenes(clip)]
    assert whole == pytest.approx(CUTS, abs=0.1)
    seen: list[tuple[int, int]] = []
    chunked = detect_scenes_chunked(
        clip, 60.0, chunk_s=20.0, overlap_s=2.0, on_progress=lambda i, n: seen.append((i, n))
    )
    times = [c.time for c in chunked]
    assert len(times) == len(whole)  # keine Doppelschnitte an Chunk-Grenzen
    assert times == pytest.approx(whole, abs=0.1)  # absolut zur Quelldatei
    assert all(c.score is not None for c in chunked)
    assert seen == [(1, 4), (2, 4), (3, 4), (4, 4)]  # Fortschritt je Chunk


def test_analyze_chunked_gives_absolute_gapless_segments(clip: Path) -> None:
    seen: list[tuple[int, int]] = []
    result = analyze_chunked(
        clip, "asset-1", chunk_s=20.0, overlap_s=2.0, on_progress=lambda i, n: seen.append((i, n))
    )
    data = json.loads(result.to_json())
    validate_analysis(data)
    segments = data["segments"]
    assert segments[0][0] == 0.0 and segments[-1][1] == pytest.approx(60.0, abs=0.1)
    assert all(a[1] == b[0] for a, b in zip(segments, segments[1:], strict=False))
    bounds = {s[0] for s in segments}
    assert all(any(abs(b - cut) <= 0.1 for b in bounds) for cut in CUTS)
    assert data["highlights"] and all(h["end"] <= 60.1 for h in data["highlights"])
    assert len(seen) == 4
    whole = json.loads(analyze_asset(clip, "asset-1").to_json())
    assert len(segments) == len(whole["segments"])
    flat = [t for seg in segments for t in seg]
    assert flat == pytest.approx([t for seg in whole["segments"] for t in seg], abs=0.1)


def test_limits_still_apply(clip: Path) -> None:
    with pytest.raises(MediaRejectedError, match="too_long"):
        analyze_chunked(clip, "asset-1", limits=MediaLimits(max_duration=30.0))
    assert CHUNKED_LIMITS.max_duration == 3 * 3600


def test_only_the_chunked_path_takes_more_than_30_minutes(long_clip: Path) -> None:
    with pytest.raises(MediaRejectedError, match="too_long"):
        analyze_asset(long_clip, "lang")
    with pytest.raises(MediaRejectedError, match="too_long"):
        analyze_asset(long_clip, "lang", limits=CHUNKED_LIMITS)  # nicht am Chunking vorbei
    with pytest.raises(MediaRejectedError, match="too_long"):
        segment_signals(long_clip, [(1800.0, 1806.0)])
    seen: list[tuple[int, int]] = []
    cuts = detect_scenes_chunked(long_clip, 1860.0, on_progress=lambda i, n: seen.append((i, n)))
    assert cuts == []
    assert seen == [(1, 4), (2, 4), (3, 4), (4, 4)]
    (late,) = segment_signals(long_clip, [(1800.0, 1806.0)], CHUNKED_LIMITS)
    assert (late.start, late.end, late.motion) == (1800.0, 1806.0, 0.0)
