import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class FfmpegNotFoundError(RuntimeError):
    """ffmpeg is not on PATH."""


@dataclass(frozen=True)
class SceneCut:
    time: float
    score: float | None


_PTS_TIME = re.compile(r"\[Parsed_showinfo_\d+ @ [^\]]+\].*?\bpts_time:(\S+)")
_SCORE = re.compile(r"lavfi\.scene_score=(\S+)")


def detect_scenes(path: Path, threshold: float = 0.3) -> list[SceneCut]:
    """Cut times (seconds) where ffmpeg's scene score exceeds threshold (0..1)."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise FfmpegNotFoundError("ffmpeg not found on PATH; install FFmpeg (ffmpeg.org)")
    proc = subprocess.run(
        [ffmpeg, "-hide_banner", "-nostdin", "-v", "info", "-i", str(path), "-map", "0:v:0",
         "-vf", f"select='gt(scene,{threshold})',metadata=print,showinfo",
         "-an", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )  # fmt: skip
    if proc.returncode != 0:
        lines = proc.stderr.strip().splitlines()
        reason = lines[-1] if lines else "ffmpeg failed"
        raise ValueError(f"{path.name}: not a readable video ({reason})")
    lines = proc.stderr.splitlines()
    times = [float(m.group(1)) for m in map(_PTS_TIME.search, lines) if m]
    scores = [float(m.group(1)) for m in map(_SCORE.search, lines) if m]
    # Every selected frame passes metadata=print and showinfo once; if the counts differ
    # the pairing is unknown, so report no score rather than a wrong one.
    paired: list[float | None] = list(scores) if len(scores) == len(times) else [None] * len(times)
    return [SceneCut(t, s) for t, s in zip(times, paired, strict=True)]


def to_segments(cuts: list[SceneCut], duration: float) -> list[tuple[float, float]]:
    """Gapless (start, end) intervals from 0 to duration; cuts outside (0, duration) are ignored."""
    points = sorted({c.time for c in cuts if 0.0 < c.time < duration})
    bounds = [0.0, *points, duration]
    return list(zip(bounds, bounds[1:], strict=False))
