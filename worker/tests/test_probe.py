import shutil
import subprocess

from probe import ok


def test_ffmpeg() -> None:
    assert ok()
    assert shutil.which("ffmpeg")
    subprocess.run(["ffprobe", "-version"], check=True)
