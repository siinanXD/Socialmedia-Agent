import subprocess
from pathlib import Path

import pytest

from socialmedia_worker.scenes import FfmpegNotFoundError
from socialmedia_worker.signals import SegmentSignal, segment_signals
from socialmedia_worker.validate import MediaRejectedError


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", *args], check=True)


@pytest.fixture
def av_clip(tmp_path: Path) -> Path:
    """0-2 s: moving noise + loud tone; 2-4 s: static colour + quiet tone."""
    path = tmp_path / "av.mp4"
    _ffmpeg(
        "-f", "lavfi", "-i", "testsrc2=duration=2:size=320x240:rate=25",
        "-f", "lavfi", "-i", "color=c=gray:duration=2:size=320x240:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2:sample_rate=44100,volume=0.8",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2:sample_rate=44100,volume=0.02",
        "-filter_complex",
        "[0:v][1:v]concat=n=2:v=1:a=0,format=yuv420p[v];[2:a][3:a]concat=n=2:v=0:a=1[a]",
        "-map", "[v]", "-map", "[a]", "-c:a", "aac", str(path),
    )  # fmt: skip
    return path


@pytest.fixture
def silent_video(tmp_path: Path) -> Path:
    path = tmp_path / "silent.mp4"
    _ffmpeg("-f", "lavfi", "-i", "testsrc2=duration=2:size=320x240:rate=25", str(path))
    return path


SEGMENTS = [(0.0, 2.0), (2.0, 4.0)]


def test_moving_segment_has_higher_motion_than_static(av_clip: Path) -> None:
    moving, static = segment_signals(av_clip, SEGMENTS)
    assert moving.motion > static.motion
    assert 0.0 <= static.motion <= moving.motion <= 1.0
    assert static.motion < 0.05


def test_loud_segment_has_higher_loudness_than_quiet(av_clip: Path) -> None:
    loud, quiet = segment_signals(av_clip, SEGMENTS)
    assert loud.loudness is not None and quiet.loudness is not None
    assert loud.loudness > quiet.loudness
    assert 0.0 <= quiet.loudness <= loud.loudness <= 1.0


def test_clip_without_audio_has_loudness_none_not_zero(silent_video: Path) -> None:
    (signal,) = segment_signals(silent_video, [(0.0, 2.0)])
    assert signal.loudness is None
    assert signal.motion > 0.0


def test_same_input_gives_same_values(av_clip: Path) -> None:
    assert segment_signals(av_clip, SEGMENTS) == segment_signals(av_clip, SEGMENTS)


def test_result_carries_segment_bounds(av_clip: Path) -> None:
    result = segment_signals(av_clip, SEGMENTS)
    assert [(s.start, s.end) for s in result] == SEGMENTS
    assert isinstance(result[0], SegmentSignal)


def test_empty_segment_list_returns_empty(av_clip: Path) -> None:
    assert segment_signals(av_clip, []) == []


def test_invalid_segment_is_rejected(av_clip: Path) -> None:
    with pytest.raises(ValueError, match="segment"):
        segment_signals(av_clip, [(2.0, 1.0)])


def test_validates_the_source_first(tmp_path: Path) -> None:
    mkv = tmp_path / "src.mkv"
    _ffmpeg("-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=25", str(mkv))
    with pytest.raises(MediaRejectedError, match="format_not_allowed"):
        segment_signals(mkv, [(0.0, 1.0)])


def test_rejects_an_image(tmp_path: Path) -> None:
    png = tmp_path / "a.png"
    _ffmpeg("-f", "lavfi", "-i", "testsrc=size=320x240", "-frames:v", "1", str(png))
    with pytest.raises(MediaRejectedError, match="not a video"):
        segment_signals(png, [(0.0, 1.0)])


def test_reports_missing_ffmpeg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: None)
    with pytest.raises(FfmpegNotFoundError, match="ffmpeg"):
        segment_signals(tmp_path / "any.mp4", [(0.0, 1.0)])
