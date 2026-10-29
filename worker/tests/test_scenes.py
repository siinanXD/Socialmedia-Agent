import subprocess
from pathlib import Path

import pytest

from socialmedia_worker.scenes import FfmpegNotFoundError, SceneCut, detect_scenes, to_segments


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", *args], check=True)


@pytest.fixture
def two_part_clip(tmp_path: Path) -> Path:
    """1 s testsrc followed by 1 s solid red: exactly one hard cut at 1.0 s."""
    path = tmp_path / "two_part.mp4"
    _ffmpeg(
        "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=25",
        "-f", "lavfi", "-i", "color=c=red:duration=1:size=320x240:rate=25",
        "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0,format=yuv420p",
        str(path),
    )  # fmt: skip
    return path


@pytest.fixture
def one_part_clip(tmp_path: Path) -> Path:
    path = tmp_path / "one_part.mp4"
    _ffmpeg("-f", "lavfi", "-i", "color=c=red:duration=1:size=320x240:rate=25", str(path))
    return path


def test_detect_scenes_finds_the_single_cut(two_part_clip: Path) -> None:
    cuts = detect_scenes(two_part_clip, threshold=0.3)
    assert len(cuts) == 1
    assert cuts[0].time == pytest.approx(1.0, abs=0.1)
    assert cuts[0].score is not None
    assert cuts[0].score > 0.3


def test_detect_scenes_returns_nothing_without_cut(one_part_clip: Path) -> None:
    assert detect_scenes(one_part_clip) == []


def test_detect_scenes_rejects_file_without_video(tmp_path: Path) -> None:
    bad = tmp_path / "bad.mp4"
    bad.write_bytes(b"not a video")
    with pytest.raises(ValueError, match="bad.mp4"):
        detect_scenes(bad)


def test_detect_scenes_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="missing.mp4"):
        detect_scenes(tmp_path / "missing.mp4")


def test_detect_scenes_reports_missing_ffmpeg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: None)
    with pytest.raises(FfmpegNotFoundError, match="ffmpeg"):
        detect_scenes(tmp_path / "any.mp4")


def test_to_segments_without_cut_is_one_segment() -> None:
    assert to_segments([], 10.0) == [(0.0, 10.0)]


def test_to_segments_is_gapless_from_zero_to_duration() -> None:
    cuts = [SceneCut(2.5, 0.8), SceneCut(6.0, None)]
    assert to_segments(cuts, 10.0) == [(0.0, 2.5), (2.5, 6.0), (6.0, 10.0)]


def test_to_segments_ignores_cuts_outside_the_clip_and_duplicates() -> None:
    cuts = [SceneCut(6.0, 0.5), SceneCut(0.0, 0.9), SceneCut(6.0, 0.4), SceneCut(12.0, 0.7)]
    assert to_segments(cuts, 10.0) == [(0.0, 6.0), (6.0, 10.0)]


def test_detect_scenes_validates_the_source_first(tmp_path: Path) -> None:
    # Codex review #10: limits and allowed containers apply before ffmpeg decodes.
    from socialmedia_worker.validate import MediaRejectedError

    mkv = tmp_path / "src.mkv"
    _ffmpeg("-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=25", str(mkv))
    with pytest.raises(MediaRejectedError, match="format_not_allowed"):
        detect_scenes(mkv)
