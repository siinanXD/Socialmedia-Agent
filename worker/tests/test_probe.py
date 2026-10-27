import subprocess
from pathlib import Path

import pytest

from socialmedia_worker.probe import FfprobeNotFoundError, probe


@pytest.fixture
def clip(tmp_path: Path) -> Path:
    path = tmp_path / "clip.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=25",
         str(path)],
        check=True,
    )
    return path


def test_probe_returns_duration_width_height(clip: Path) -> None:
    result = probe(clip)
    assert (result.width, result.height) == (320, 240)
    assert result.duration == pytest.approx(1.0, abs=0.1)


def test_probe_rejects_file_without_video(tmp_path: Path) -> None:
    bad = tmp_path / "bad.mp4"
    bad.write_bytes(b"not a video")
    with pytest.raises(ValueError, match="bad.mp4"):
        probe(bad)


def test_probe_reports_missing_ffprobe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: None)
    with pytest.raises(FfprobeNotFoundError, match="ffprobe"):
        probe(tmp_path / "any.mp4")
