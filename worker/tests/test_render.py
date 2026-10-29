import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from socialmedia_worker.probe import probe
from socialmedia_worker.render import (
    FfmpegNotFoundError,
    RenderError,
    extract_cover,
    render_vertical,
)
from socialmedia_worker.validate import MediaRejectedError, validate_media


def _make_source(path: Path, *, audio: bool) -> Path:
    cmd = ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=duration=4:size=1280x720:rate=25"]
    if audio:
        cmd += ["-f", "lavfi", "-i", "sine=frequency=440:duration=4", "-c:a", "aac"]
    subprocess.run([*cmd, "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def _stream_types(path: Path) -> list[str]:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type",
            "-print_format",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [s["codec_type"] for s in json.loads(out)["streams"]]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def src(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _make_source(tmp_path_factory.mktemp("source") / "src.mp4", audio=True)


def test_render_vertical_outputs_1080x1920_for_the_range(src: Path, tmp_path: Path) -> None:
    before = _sha256(src)
    out = tmp_path / "out.mp4"
    result = render_vertical(src, start=1.0, end=3.0, out=out)
    info = probe(out)
    assert (info.width, info.height) == (1080, 1920)
    assert info.duration == pytest.approx(2.0, abs=0.2)
    assert result.path == out
    assert (result.width, result.height) == (1080, 1920)
    assert result.duration == pytest.approx(info.duration)
    assert _stream_types(out) == ["video", "audio"]
    assert _sha256(src) == before


def test_render_vertical_handles_source_without_audio(tmp_path: Path) -> None:
    silent = _make_source(tmp_path / "silent.mp4", audio=False)
    out = tmp_path / "out.mp4"
    render_vertical(silent, start=0.0, end=2.0, out=out)
    assert _stream_types(out) == ["video"]
    assert (probe(out).width, probe(out).height) == (1080, 1920)


@pytest.mark.parametrize(("start", "end"), [(-1.0, 2.0), (2.0, 2.0), (3.0, 1.0), (0.0, 5.0)])
def test_render_vertical_rejects_invalid_range(
    src: Path, tmp_path: Path, start: float, end: float
) -> None:
    out = tmp_path / "out.mp4"
    with pytest.raises(ValueError, match="range"):
        render_vertical(src, start=start, end=end, out=out)
    assert not out.exists()


def test_render_vertical_rejects_out_equal_to_src(src: Path) -> None:
    before = _sha256(src)
    with pytest.raises(ValueError, match="src"):
        render_vertical(src, start=0.0, end=1.0, out=src)
    assert _sha256(src) == before


def test_render_vertical_reports_missing_ffmpeg(
    src: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_which = __import__("shutil").which
    monkeypatch.setattr("shutil.which", lambda n: None if n == "ffmpeg" else real_which(n))
    with pytest.raises(FfmpegNotFoundError, match="ffmpeg"):
        render_vertical(src, start=0.0, end=1.0, out=tmp_path / "out.mp4")


def test_render_vertical_failure_deletes_partial_output(src: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.unknownext"
    with pytest.raises(RenderError):
        render_vertical(src, start=0.0, end=1.0, out=out)
    assert not out.exists()


def test_extract_cover_writes_readable_jpeg(src: Path, tmp_path: Path) -> None:
    out = tmp_path / "cover.jpg"
    assert extract_cover(src, at=1.5, out=out) == out
    assert out.read_bytes()[:3] == b"\xff\xd8\xff"
    info = probe(out)
    assert (info.width, info.height) == (1280, 720)


def test_extract_cover_from_rendered_clip_is_vertical(src: Path, tmp_path: Path) -> None:
    clip = tmp_path / "clip.mp4"
    render_vertical(src, start=1.0, end=3.0, out=clip)
    cover = extract_cover(clip, at=1.0, out=tmp_path / "cover.jpg")
    info = probe(cover)
    assert (info.width, info.height) == (1080, 1920)


@pytest.mark.parametrize("at", [9.0, -0.5])
def test_extract_cover_rejects_time_outside_video(src: Path, tmp_path: Path, at: float) -> None:
    with pytest.raises(ValueError, match="at"):
        extract_cover(src, at=at, out=tmp_path / "cover.jpg")
    assert not (tmp_path / "cover.jpg").exists()


def test_extract_cover_rejects_time_at_end_of_video(src: Path, tmp_path: Path) -> None:
    # Codex review SIN-1166: at == duration lies after the last frame and ffmpeg writes nothing.
    duration = probe(src).duration
    with pytest.raises(ValueError, match="at"):
        extract_cover(src, at=duration, out=tmp_path / "cover.jpg")


def test_output_is_never_overwritten(src: Path, tmp_path: Path) -> None:
    out = tmp_path / "taken.mp4"
    out.write_bytes(b"earlier render")
    with pytest.raises(FileExistsError, match="overwrite"):
        render_vertical(src, start=0.0, end=1.0, out=out)
    with pytest.raises(FileExistsError, match="overwrite"):
        extract_cover(src, at=1.0, out=out)
    assert out.read_bytes() == b"earlier render"


def test_render_timeout_is_reported_and_leaves_no_output(
    src: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_run = subprocess.run

    def hang(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if Path(cmd[0]).stem == "ffmpeg":
            raise subprocess.TimeoutExpired(cmd, 1.0)
        result: subprocess.CompletedProcess[str] = real_run(cmd, **kwargs)  # type: ignore[call-overload]
        return result

    monkeypatch.setattr("socialmedia_worker.render.subprocess.run", hang)
    out = tmp_path / "out.mp4"
    with pytest.raises(RenderError, match="timed out"):
        render_vertical(src, start=0.0, end=1.0, out=out)
    assert not out.exists()


def test_extract_cover_accepts_jpeg_without_duration(
    src: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Codex review SIN-1166 (P1): some ffprobe builds report a JPEG without format.duration;
    # probe() then raises. The cover must be checked as an image, not as a video.
    import socialmedia_worker.render as render

    real_probe = probe

    def video_only(path: Path) -> object:
        if path.suffix == ".jpg":
            raise ValueError(f"{path.name}: not a readable video (no duration)")
        return real_probe(path)

    monkeypatch.setattr(render, "probe", video_only)
    out = tmp_path / "cover.jpg"
    assert extract_cover(src, at=1.5, out=out) == out
    media = validate_media(out)
    assert (media.kind, media.width, media.height) == ("image", 1280, 720)
    assert media.duration is None


def test_extract_cover_deletes_output_that_is_not_an_image(
    src: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import socialmedia_worker.render as render

    def broken(path: Path, limits: object = None) -> object:
        raise MediaRejectedError("unsupported_format", f"{path.name}: not a supported media file")

    monkeypatch.setattr(render, "validate_media", broken)
    out = tmp_path / "cover.jpg"
    with pytest.raises(RenderError, match="not a readable image"):
        extract_cover(src, at=1.5, out=out)
    assert not out.exists()


def test_extract_cover_rejects_out_equal_to_video(src: Path) -> None:
    with pytest.raises(ValueError, match="video"):
        extract_cover(src, at=1.0, out=src)
