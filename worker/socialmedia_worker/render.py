import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from socialmedia_worker.probe import probe

WIDTH, HEIGHT = 1080, 1920
# Centre crop: scale to cover 1080x1920, then crop the overflow.
_VERTICAL_FILTER = (
    f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
    f"crop={WIDTH}:{HEIGHT},setsar=1"
)


class FfmpegNotFoundError(RuntimeError):
    """ffmpeg is not on PATH."""


class RenderError(RuntimeError):
    """ffmpeg exited with a non-zero status."""


@dataclass(frozen=True)
class RenderResult:
    path: Path
    duration: float
    width: int
    height: int


def _run_ffmpeg(args: list[str], out: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise FfmpegNotFoundError("ffmpeg not found on PATH; install FFmpeg (ffmpeg.org)")
    proc = subprocess.run(
        [ffmpeg, "-v", "error", "-nostdin", "-y", *args, str(out)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        out.unlink(missing_ok=True)
        tail = "\n".join(proc.stderr.strip().splitlines()[-5:])
        raise RenderError(f"ffmpeg failed with exit code {proc.returncode}: {tail}")


def render_vertical(src: Path, start: float, end: float, out: Path) -> RenderResult:
    """Render src[start:end] as a 1080x1920 H.264/AAC MP4 (centre crop). src is never modified."""
    if out.resolve() == src.resolve():
        raise ValueError("out must differ from src; the original is never overwritten")
    duration = probe(src).duration
    if not 0 <= start < end <= duration:
        raise ValueError(
            f"invalid range: need 0 <= start < end <= {duration:.2f}s, got {start}..{end}"
        )
    _run_ffmpeg(
        ["-ss", str(start), "-i", str(src), "-t", str(end - start),
         "-map", "0:v:0", "-map", "0:a:0?",  # audio only if the source has any
         "-vf", _VERTICAL_FILTER,
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
         "-movflags", "+faststart"],
        out,
    )
    info = probe(out)
    return RenderResult(out, info.duration, info.width, info.height)


def extract_cover(video: Path, at: float, out: Path) -> Path:
    """Write the frame of video at `at` seconds as a JPEG to out."""
    if out.resolve() == video.resolve():
        raise ValueError("out must differ from video; the original is never overwritten")
    duration = probe(video).duration
    if not 0 <= at <= duration:
        raise ValueError(f"invalid at: need 0 <= at <= {duration:.2f}s, got {at}")
    _run_ffmpeg(["-ss", str(at), "-i", str(video), "-frames:v", "1", "-q:v", "2"], out)
    return out
