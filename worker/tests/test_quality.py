import subprocess
from pathlib import Path

import pytest

from socialmedia_worker.quality import Quality, image_quality
from socialmedia_worker.render import extract_cover
from socialmedia_worker.scenes import FfmpegNotFoundError
from socialmedia_worker.validate import MediaRejectedError


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", *args], check=True)


def _variant(src: Path, name: str, vf: str) -> Path:
    out = src.parent / name
    _ffmpeg("-i", str(src), "-vf", vf, "-frames:v", "1", str(out))
    return out


@pytest.fixture
def sharp(tmp_path: Path) -> Path:
    path = tmp_path / "sharp.png"
    _ffmpeg("-f", "lavfi", "-i", "testsrc2=size=640x480", "-frames:v", "1", str(path))
    return path


def test_sharp_well_exposed_image_has_no_reasons(sharp: Path) -> None:
    q = image_quality(sharp)
    assert isinstance(q, Quality)
    assert 0.0 <= q.sharpness <= 1.0
    assert 0.0 <= q.exposure <= 1.0
    assert q.reasons == []


def test_blurred_image_is_less_sharp_with_reason(sharp: Path) -> None:
    blurred = image_quality(_variant(sharp, "blur.png", "gblur=sigma=8"))
    assert blurred.sharpness < image_quality(sharp).sharpness
    assert "unscharf" in blurred.reasons


def test_dark_image_has_lower_exposure_with_reason(sharp: Path) -> None:
    dark = image_quality(_variant(sharp, "dark.png", "eq=brightness=-0.6"))
    assert dark.exposure < image_quality(sharp).exposure
    assert "unterbelichtet" in dark.reasons


def test_bright_image_has_lower_exposure_with_reason(sharp: Path) -> None:
    bright = image_quality(_variant(sharp, "bright.png", "eq=brightness=0.8"))
    assert bright.exposure < image_quality(sharp).exposure
    assert "überbelichtet" in bright.reasons


def test_same_input_gives_same_values(sharp: Path) -> None:
    assert image_quality(sharp) == image_quality(sharp)


def test_works_for_a_frame_taken_from_a_video(tmp_path: Path) -> None:
    clip = tmp_path / "clip.mp4"
    _ffmpeg("-f", "lavfi", "-i", "testsrc2=duration=2:size=640x480:rate=25", str(clip))
    cover = extract_cover(clip, at=1.0, out=tmp_path / "cover.jpg")
    q = image_quality(cover)
    assert q.sharpness > 0.0
    assert q.reasons == []


def test_rejects_a_video(tmp_path: Path) -> None:
    clip = tmp_path / "clip.mp4"
    _ffmpeg("-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=25", str(clip))
    with pytest.raises(MediaRejectedError, match="not an image"):
        image_quality(clip)


def test_validates_the_source_first(tmp_path: Path) -> None:
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"not an image")
    with pytest.raises(MediaRejectedError, match="truncated_or_corrupt"):
        image_quality(bad)


def test_reports_missing_ffmpeg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: None)
    with pytest.raises(FfmpegNotFoundError, match="ffmpeg"):
        image_quality(tmp_path / "any.png")
