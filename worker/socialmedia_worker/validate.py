import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from socialmedia_worker.probe import FfprobeNotFoundError

MAX_UPLOAD_MB = 500
PROBE_TIMEOUT_S = 30

Reason = Literal[
    "unsafe_path",
    "not_found",
    "too_large",
    "unsupported_format",
    "truncated_or_corrupt",
    "format_not_allowed",
    "no_video_stream",
    "too_long",
    "resolution_too_high",
    "probe_timeout",
]

_IMAGE_FORMATS = {"jpeg_pipe", "png_pipe"}
# First bytes of formats we can recognise as "meant to be media, but broken" (vs. random data).
_MP4_BOX_TYPES = {b"ftyp", b"moov", b"mdat", b"free", b"wide", b"skip"}
_IMAGE_MAGIC = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")


class MediaRejectedError(ValueError):
    """Source file rejected; `reason` is a stable machine-readable code."""

    def __init__(self, reason: Reason, message: str) -> None:
        super().__init__(f"{reason}: {message}")
        self.reason = reason


@dataclass(frozen=True)
class MediaLimits:
    """Defaults: 500 MB, 30 min, 8K pixels, MP4/MOV video and JPEG/PNG images.

    `allowed_formats` holds ffprobe format names; add "webm" to accept WebM.
    """

    max_bytes: int = MAX_UPLOAD_MB * 1024 * 1024
    max_duration: float = 30 * 60
    max_pixels: int = 7680 * 4320
    allowed_formats: frozenset[str] = field(
        default_factory=lambda: frozenset({"mov", "mp4", "jpeg_pipe", "png_pipe"})
    )


@dataclass(frozen=True)
class ValidatedMedia:
    kind: Literal["video", "image"]
    container: str
    codec: str
    size_bytes: int
    sha256: str
    duration: float | None
    width: int
    height: int


def _ffprobe(path: Path) -> dict[str, Any] | None:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise FfprobeNotFoundError("ffprobe not found on PATH; install FFmpeg (ffmpeg.org)")
    try:
        proc = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries",
             "stream=codec_type,codec_name,width,height:format=format_name,duration",
             "-print_format", "json", str(path)],
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as exc:
        raise MediaRejectedError("probe_timeout", f"{path.name}: ffprobe timed out") from exc
    if proc.returncode != 0:
        return None
    data: dict[str, Any] = json.loads(proc.stdout)
    return data


def _looks_like_media(path: Path) -> bool:
    with path.open("rb") as f:
        head = f.read(12)
    return head[4:8] in _MP4_BOX_TYPES or head.startswith(_IMAGE_MAGIC)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def validate_media(path: Path, limits: MediaLimits | None = None) -> ValidatedMedia:
    """Check type (by content, not extension), size, duration and resolution; read-only."""
    limits = limits or MediaLimits()
    if ".." in path.parts or str(path).startswith("-"):
        raise MediaRejectedError("unsafe_path", f"{path}: '..' or leading '-' not allowed")
    if not path.is_file():
        raise MediaRejectedError("not_found", f"{path.name}: not a file")
    size = path.stat().st_size
    if size > limits.max_bytes:
        raise MediaRejectedError("too_large", f"{path.name}: {size} > {limits.max_bytes} bytes")

    data = _ffprobe(path)
    if data is None or not data.get("streams"):
        if _looks_like_media(path):
            # shortcut: a cut file whose index sits at the front still probes fine and passes
            raise MediaRejectedError("truncated_or_corrupt", f"{path.name}: unreadable media")
        raise MediaRejectedError("unsupported_format", f"{path.name}: not a supported media file")

    container = str(data["format"]["format_name"])
    if not set(container.split(",")) & limits.allowed_formats:
        raise MediaRejectedError("format_not_allowed", f"{path.name}: {container}")
    stream = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    if stream is None:
        raise MediaRejectedError("no_video_stream", f"{path.name}: no video stream")

    kind: Literal["video", "image"] = "image" if container in _IMAGE_FORMATS else "video"
    duration = None
    if kind == "video":
        if "duration" not in data["format"]:
            raise MediaRejectedError("truncated_or_corrupt", f"{path.name}: no duration")
        duration = float(data["format"]["duration"])
        if duration > limits.max_duration:
            raise MediaRejectedError(
                "too_long", f"{path.name}: {duration:.0f}s > {limits.max_duration:.0f}s"
            )
    width, height = int(stream["width"]), int(stream["height"])
    if width * height > limits.max_pixels:
        raise MediaRejectedError(
            "resolution_too_high", f"{path.name}: {width}x{height} > {limits.max_pixels} px"
        )

    return ValidatedMedia(
        kind, container, str(stream["codec_name"]), size, _sha256(path), duration, width, height
    )
