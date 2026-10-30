import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from socialmedia_worker.scenes import FfmpegNotFoundError
from socialmedia_worker.validate import MediaRejectedError, validate_media

FFMPEG_TIMEOUT_S = 300
# signalstats YDIF is the mean absolute luma difference (0..255) between consecutive frames.
# 20 is a strong, clearly visible change; anything above counts as full motion.
MOTION_FULL_SCALE = 20.0
# volumedetect mean_volume in dBFS: -60 dB and below counts as silence, 0 dB as full scale.
LOUDNESS_FLOOR_DB = -60.0

_MEAN_VOLUME = re.compile(r"mean_volume:\s*(-?\d+(?:\.\d+)?|-inf) dB")


@dataclass(frozen=True)
class SegmentSignal:
    start: float
    end: float
    motion: float
    loudness: float | None


def ffmpeg_path() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise FfmpegNotFoundError("ffmpeg not found on PATH; install FFmpeg (ffmpeg.org)")
    return ffmpeg


def filter_values(args: list[str], key: str, name: str) -> list[float]:
    """Run ffmpeg with `args` (ending in a metadata=print:file=- filter) and return the values
    of metadata `key` in frame order. `name` is only used for error messages."""
    proc = subprocess.run(
        [ffmpeg_path(), "-hide_banner", "-nostdin", "-v", "error", *args, "-an", "-f", "null", "-"],
        capture_output=True,
        text=True,
        timeout=FFMPEG_TIMEOUT_S,
    )
    if proc.returncode != 0:
        lines = proc.stderr.strip().splitlines()
        raise ValueError(f"{name}: ffmpeg failed ({lines[-1] if lines else 'no output'})")
    prefix = f"{key}="
    return [
        float(line[len(prefix) :]) for line in proc.stdout.splitlines() if line.startswith(prefix)
    ]


def _has_audio(path: Path) -> bool:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:  # validate_media would already have failed; keep mypy and callers honest
        raise FileNotFoundError("ffprobe not found on PATH")
    proc = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
         "-of", "csv=p=0", str(path)],
        capture_output=True,
        text=True,
        timeout=30,
    )  # fmt: skip
    return proc.returncode == 0 and bool(proc.stdout.strip())


def _motion(path: Path, start: float, end: float) -> float:
    ydif = filter_values(
        ["-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", str(path), "-map", "0:v:0",
         "-vf", "signalstats,metadata=print:file=-"],
        "lavfi.signalstats.YDIF",
        path.name,
    )  # fmt: skip
    # The first frame has no predecessor; its 0 would only dilute short segments.
    values = ydif[1:] or ydif
    mean = sum(values) / len(values) if values else 0.0
    return round(min(mean / MOTION_FULL_SCALE, 1.0), 4)


def _loudness(path: Path, start: float, end: float) -> float:
    proc = subprocess.run(
        [ffmpeg_path(), "-hide_banner", "-nostdin", "-v", "info",
         "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", str(path),
         "-map", "0:a:0", "-af", "volumedetect", "-vn", "-f", "null", "-"],
        capture_output=True,
        text=True,
        timeout=FFMPEG_TIMEOUT_S,
    )  # fmt: skip
    if proc.returncode != 0:
        raise ValueError(f"{path.name}: ffmpeg failed to read audio")
    match = _MEAN_VOLUME.search(proc.stderr)
    # No match: the segment holds no audio samples (e.g. it starts after the audio ends).
    db = float(match.group(1)) if match else float("-inf")
    return round(min(max((db - LOUDNESS_FLOOR_DB) / -LOUDNESS_FLOOR_DB, 0.0), 1.0), 4)


def segment_signals(path: Path, segments: list[tuple[float, float]]) -> list[SegmentSignal]:
    """Per (start, end) segment in seconds: motion and loudness, each normalised to 0..1.

    motion: mean `signalstats` YDIF (luma change between consecutive frames, 0..255) divided by
    20 and capped at 1; a static image gives 0. loudness: `volumedetect` mean_volume in dBFS,
    mapped linearly from -60 dB (0.0) to 0 dB (1.0). A video without an audio track gives
    loudness=None, a silent track 0.0. Deterministic heuristics, no model; they say nothing
    about reach or virality. The source is checked with validate_media before ffmpeg runs.
    """
    ffmpeg_path()
    if validate_media(path).kind != "video":
        raise MediaRejectedError("unsupported_format", f"{path.name}: not a video")
    for start, end in segments:
        if not 0 <= start < end:
            raise ValueError(f"invalid segment: ({start}, {end}), need 0 <= start < end")
    audio = _has_audio(path) if segments else False
    return [
        SegmentSignal(
            float(start),
            float(end),
            _motion(path, start, end),
            _loudness(path, start, end) if audio else None,
        )
        for start, end in segments
    ]
