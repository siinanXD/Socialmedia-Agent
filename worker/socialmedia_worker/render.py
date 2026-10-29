import os
import shutil
import subprocess
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from socialmedia_worker.probe import ProbeResult, probe
from socialmedia_worker.validate import MediaRejectedError, validate_media

WIDTH, HEIGHT = 1080, 1920
# A hung ffmpeg must not block the worker (Codex review SIN-1166):
# generous for renders, short for a single frame.
RENDER_TIMEOUT_S = 600
COVER_TIMEOUT_S = 60
# Square pixels first (keeps display proportions of anamorphic sources, Codex #10),
# then scale to cover 1080x1920 and crop the overflow.
_VERTICAL_FILTER = (
    "scale=trunc(iw*sar/2)*2:ih,setsar=1,"
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


def _source_duration(src: Path) -> float:
    """Validate src (container, size, duration, resolution) before ffmpeg touches it (Codex #10)."""
    media = validate_media(src)
    if media.kind != "video" or media.duration is None:
        raise MediaRejectedError("unsupported_format", f"{src.name}: not a video")
    return media.duration


def _run_ffmpeg(
    args: list[str], out: Path, timeout: float, verify: Callable[[Path], None] | None = None
) -> None:
    """Render into a file of this call only, then publish it to out without overwriting anything."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise FfmpegNotFoundError("ffmpeg not found on PATH; install FFmpeg (ffmpeg.org)")
    taken = f"{out} exists; refusing to overwrite (originals and earlier renders stay immutable)"
    if out.exists():
        raise FileExistsError(taken)
    tmp = out.with_name(f".{out.stem}.{uuid.uuid4().hex}{out.suffix}")
    try:
        try:
            proc = subprocess.run(
                [ffmpeg, "-v", "error", "-nostdin", "-n", *args, str(tmp)],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise RenderError(f"ffmpeg timed out after {timeout:.0f}s") from exc
        if proc.returncode != 0:
            tail = "\n".join(proc.stderr.strip().splitlines()[-5:])
            raise RenderError(f"ffmpeg failed with exit code {proc.returncode}: {tail}")
        if not tmp.exists() or tmp.stat().st_size == 0:
            raise RenderError("ffmpeg exited 0 but wrote no output")
        if verify is not None:
            verify(tmp)
        # Claim out exclusively; a concurrent call that got there first keeps its file.
        try:
            os.close(os.open(out, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        except FileExistsError as exc:
            raise FileExistsError(taken) from exc
        os.replace(tmp, out)
    finally:
        tmp.unlink(missing_ok=True)


def render_vertical(src: Path, start: float, end: float, out: Path) -> RenderResult:
    """Render src[start:end] as a 1080x1920 H.264/AAC MP4 (centre crop). src is never modified."""
    if out.resolve() == src.resolve():
        raise ValueError("out must differ from src; the original is never overwritten")
    duration = _source_duration(src)
    if not 0 <= start < end <= duration:
        raise ValueError(
            f"invalid range: need 0 <= start < end <= {duration:.2f}s, got {start}..{end}"
        )
    checked: list[ProbeResult] = []
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
        lambda path: checked.append(_check_render(path)),
    )
    info = checked[0]
    return RenderResult(out, info.duration, info.width, info.height)


def _check_render(path: Path) -> ProbeResult:
    # Check before publishing (Codex #10): e.g. a range in the audio tail yields no video frames.
    try:
        return probe(path)
    except ValueError as exc:
        raise RenderError(f"render is not a readable video: {exc}") from exc


def extract_cover(video: Path, at: float, out: Path) -> Path:
    """Write the frame of video at `at` seconds as a JPEG to out; verify it is a readable image."""
    if out.resolve() == video.resolve():
        raise ValueError("out must differ from video; the original is never overwritten")
    duration = _source_duration(video)
    # `at == duration` lies after the last frame: ffmpeg exits 0 without an image.
    if not 0 <= at < duration:
        raise ValueError(f"invalid at: need 0 <= at < {duration:.2f}s, got {at}")
    _run_ffmpeg(
        ["-ss", str(at), "-i", str(video), "-frames:v", "1", "-q:v", "2"],
        out,
        COVER_TIMEOUT_S,
        _check_cover,
    )
    return out


def _check_cover(path: Path) -> None:
    # An image has no duration: check it as an image (SIN-1173), not with probe() (Codex P1).
    try:
        if validate_media(path).kind != "image":
            raise MediaRejectedError("unsupported_format", f"{path.name}: not an image")
    except MediaRejectedError as exc:
        raise RenderError(f"cover is not a readable image: {exc}") from exc
