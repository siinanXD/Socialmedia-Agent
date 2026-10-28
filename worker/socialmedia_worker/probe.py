import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class FfprobeNotFoundError(RuntimeError):
    """ffprobe is not on PATH."""


@dataclass(frozen=True)
class ProbeResult:
    duration: float
    width: int
    height: int


def probe(path: Path) -> ProbeResult:
    """Read duration (seconds) and size of the first video stream via ffprobe."""
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise FfprobeNotFoundError("ffprobe not found on PATH; install FFmpeg (ffmpeg.org)")
    proc = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height:format=duration",
            "-print_format",
            "json",
            "-i",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    try:
        data = json.loads(proc.stdout)
        stream = data["streams"][0]
        duration = float(data["format"]["duration"])
        return ProbeResult(duration, int(stream["width"]), int(stream["height"]))
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        reason = proc.stderr.strip() or "no video stream"
        raise ValueError(f"{path.name}: not a readable video ({reason})") from exc
