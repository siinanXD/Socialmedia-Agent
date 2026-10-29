import hashlib
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from socialmedia_worker.probe import FfprobeNotFoundError
from socialmedia_worker.validate import MediaLimits, MediaRejectedError, validate_media


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


@pytest.fixture
def video(tmp_path: Path) -> Path:
    path = tmp_path / "clip.mp4"
    _ffmpeg("-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=25", "-pix_fmt", "yuv420p",
            str(path))
    return path


@pytest.fixture(params=["jpg", "png"])
def image(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    path = tmp_path / f"pic.{request.param}"
    _ffmpeg("-f", "lavfi", "-i", "testsrc=size=64x48", "-frames:v", "1", str(path))
    return path


def _reason(path: Path, limits: MediaLimits | None = None) -> str:
    with pytest.raises(MediaRejectedError) as info:
        validate_media(path, limits) if limits else validate_media(path)
    return info.value.reason


def test_valid_video(video: Path) -> None:
    result = validate_media(video)
    assert result.kind == "video"
    assert (result.width, result.height) == (320, 240)
    assert result.duration == pytest.approx(2.0, abs=0.1)
    assert result.size_bytes == video.stat().st_size
    assert result.sha256 == hashlib.sha256(video.read_bytes()).hexdigest()
    assert "mp4" in result.container
    assert result.codec == "h264"


def test_valid_image_has_no_duration(image: Path) -> None:
    result = validate_media(image)
    assert result.kind == "image"
    assert (result.width, result.height) == (64, 48)
    assert result.duration is None
    assert result.sha256 == hashlib.sha256(image.read_bytes()).hexdigest()


def test_source_file_stays_byte_identical(video: Path) -> None:
    before = (video.read_bytes(), video.stat().st_mtime_ns)
    validate_media(video)
    assert (video.read_bytes(), video.stat().st_mtime_ns) == before


def test_rejects_text_file_with_mp4_extension(tmp_path: Path) -> None:
    fake = tmp_path / "fake.mp4"
    fake.write_text("this is not a video")
    assert _reason(fake) == "unsupported_format"


def test_rejects_truncated_file(video: Path, tmp_path: Path) -> None:
    cut = tmp_path / "cut.mp4"
    cut.write_bytes(video.read_bytes()[:3000])
    assert _reason(cut) == "truncated_or_corrupt"


def test_rejects_too_large(video: Path) -> None:
    assert _reason(video, replace(MediaLimits(), max_bytes=1000)) == "too_large"


def test_rejects_too_long(video: Path) -> None:
    assert _reason(video, replace(MediaLimits(), max_duration=1.0)) == "too_long"


def test_rejects_too_many_pixels(video: Path) -> None:
    assert _reason(video, replace(MediaLimits(), max_pixels=100)) == "resolution_too_high"


def test_rejects_format_not_in_allowlist(video: Path) -> None:
    only_images = replace(MediaLimits(), allowed_formats=frozenset({"jpeg_pipe", "png_pipe"}))
    assert _reason(video, only_images) == "format_not_allowed"


def test_rejects_audio_only_file(tmp_path: Path) -> None:
    audio = tmp_path / "sound.m4a"
    _ffmpeg("-f", "lavfi", "-i", "sine=duration=1", "-c:a", "aac", str(audio))
    assert _reason(audio) == "no_video_stream"


def test_rejects_missing_file(tmp_path: Path) -> None:
    assert _reason(tmp_path / "nope.mp4") == "not_found"


@pytest.mark.parametrize("bad", ["../clip.mp4", "-clip.mp4", "sub/../clip.mp4"])
def test_rejects_unsafe_path(bad: str) -> None:
    assert _reason(Path(bad)) == "unsafe_path"


def test_reports_missing_ffprobe(video: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: None)
    with pytest.raises(FfprobeNotFoundError, match="ffprobe"):
        validate_media(video)


@pytest.mark.parametrize("suffix", ["jpg", "png"])
def test_full_size_image_files_are_accepted(tmp_path: Path, suffix: str) -> None:
    # Small images probe as jpeg_pipe/png_pipe, real-size .jpg files as "image2" (SIN-1166).
    path = tmp_path / f"foto.{suffix}"
    _ffmpeg("-f", "lavfi", "-i", "testsrc=size=1280x720", "-frames:v", "1", str(path))
    result = validate_media(path)
    assert (result.kind, result.width, result.height, result.duration) == ("image", 1280, 720, None)
    assert result.container in {"jpeg_pipe", "png_pipe"}
