import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from socialmedia_worker.probe import probe
from socialmedia_worker.validate import MediaRejectedError, validate_media

WIDTH, HEIGHT = 1080, 1920
# A hung ffmpeg must not block the worker (Codex review SIN-1166):
# generous for renders, short for a single frame.
RENDER_TIMEOUT_S = 600
COVER_TIMEOUT_S = 60
# Centre crop: scale to cover 1080x1920, then crop the overflow.
_VERTICAL_FILTER = (
    f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT},setsar=1"
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


def _run_ffmpeg(args: list[str], out: Path, timeout: float) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise FfmpegNotFoundError("ffmpeg not found on PATH; install FFmpeg (ffmpeg.org)")
    if out.exists():
        raise FileExistsError(
            f"{out} exists; refusing to overwrite (originals and earlier renders stay immutable)"
        )
    try:
        proc = subprocess.run(
            [ffmpeg, "-v", "error", "-nostdin", "-n", *args, str(out)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        out.unlink(missing_ok=True)
        raise RenderError(f"ffmpeg timed out after {timeout:.0f}s") from exc
    if proc.returncode != 0:
        out.unlink(missing_ok=True)
        tail = "\n".join(proc.stderr.strip().splitlines()[-5:])
        raise RenderError(f"ffmpeg failed with exit code {proc.returncode}: {tail}")
    if not out.exists() or out.stat().st_size == 0:
        out.unlink(missing_ok=True)
        raise RenderError("ffmpeg exited 0 but wrote no output")


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
        [
            "-ss",
            str(start),
            "-i",
            str(src),
            "-t",
            str(end - start),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",  # audio only if the source has any
            "-vf",
            _VERTICAL_FILTER,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
        ],
        out,
        RENDER_TIMEOUT_S,
    )
    info = probe(out)
    return RenderResult(out, info.duration, info.width, info.height)


def extract_cover(video: Path, at: float, out: Path) -> Path:
    """Write the frame of video at `at` seconds as a JPEG to out; verify it is a readable image."""
    if out.resolve() == video.resolve():
        raise ValueError("out must differ from video; the original is never overwritten")
    duration = probe(video).duration
    # `at == duration` lies after the last frame: ffmpeg exits 0 without an image.
    if not 0 <= at < duration:
        raise ValueError(f"invalid at: need 0 <= at < {duration:.2f}s, got {at}")
    _run_ffmpeg(
        ["-ss", str(at), "-i", str(video), "-frames:v", "1", "-q:v", "2"], out, COVER_TIMEOUT_S
    )
    # An image has no duration: check it as an image (SIN-1173), not with probe() (Codex P1).
    try:
        if validate_media(out).kind != "image":
            raise MediaRejectedError("unsupported_format", f"{out.name}: not an image")
    except MediaRejectedError as exc:
        out.unlink(missing_ok=True)
        raise RenderError(f"cover is not a readable image: {exc}") from exc
    return out
