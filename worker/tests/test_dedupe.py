import subprocess
from pathlib import Path

import pytest

from socialmedia_worker.dedupe import (
    MAX_DISTANCE,
    drop_near_duplicates,
    frame_hash,
    hamming,
    highlight_id,
)
from socialmedia_worker.highlights import Highlight
from socialmedia_worker.validate import MediaRejectedError


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", *args], check=True)


def _clip(path: Path, source: str, vf: str | None = None) -> Path:
    args = ["-f", "lavfi", "-i", f"{source}=duration=2:size=640x360:rate=25"]
    if vf:
        args += ["-vf", vf]
    _ffmpeg(*args, "-pix_fmt", "yuv420p", str(path))
    return path


def _h(asset: str, start: float, confidence: float) -> Highlight:
    return Highlight(asset, start, start + 3.0, confidence, "Test", "test-1")


def test_hamming_counts_differing_bits() -> None:
    assert hamming(0b1011, 0b0010) == 2
    assert hamming(7, 7) == 0


def test_same_source_with_noise_and_brightness_is_a_duplicate(tmp_path: Path) -> None:
    a = frame_hash(_clip(tmp_path / "a.mp4", "testsrc2"), at=1.0)
    b = frame_hash(
        _clip(tmp_path / "b.mp4", "testsrc2", "eq=brightness=0.06,noise=alls=12:allf=t"), at=1.0
    )
    assert 0 <= a < 2**64
    assert hamming(a, b) <= MAX_DISTANCE


def test_different_sources_are_not_duplicates(tmp_path: Path) -> None:
    a = frame_hash(_clip(tmp_path / "a.mp4", "testsrc2"), at=1.0)
    c = frame_hash(_clip(tmp_path / "c.mp4", "smptebars"), at=1.0)
    assert hamming(a, c) > MAX_DISTANCE


def test_frame_hash_is_deterministic_and_works_for_images(tmp_path: Path) -> None:
    clip = _clip(tmp_path / "a.mp4", "testsrc2")
    assert frame_hash(clip, at=1.0) == frame_hash(clip, at=1.0)
    for name in ("a.png", "a.jpg"):
        _ffmpeg("-ss", "1", "-i", str(clip), "-frames:v", "1", str(tmp_path / name))
        assert hamming(frame_hash(tmp_path / name), frame_hash(clip, at=1.0)) <= MAX_DISTANCE


def test_frame_hash_rejects_time_outside_the_clip_and_bad_files(tmp_path: Path) -> None:
    clip = _clip(tmp_path / "a.mp4", "testsrc2")
    with pytest.raises(ValueError, match="invalid at"):
        frame_hash(clip, at=2.0)
    bad = tmp_path / "bad.mp4"
    bad.write_bytes(b"kein video")
    with pytest.raises(MediaRejectedError):
        frame_hash(bad, at=0.0)


def test_higher_confidence_wins_and_dropped_names_the_winner() -> None:
    low, high, other = _h("a", 0.0, 0.4), _h("b", 5.0, 0.9), _h("c", 1.0, 0.1)
    kept, dropped = drop_near_duplicates([low, high, other], [0b1111, 0b1110, 2**64 - 1])
    assert kept == [high, other]  # input order
    assert [(d.highlight, d.reason) for d in dropped] == [
        (low, f"near_duplicate_of:{highlight_id(high)}")
    ]
    assert highlight_id(high) == "b@5.000"


def test_tie_keeps_the_earlier_highlight_whatever_the_input_order() -> None:
    early, late = _h("a", 1.0, 0.5), _h("a", 9.0, 0.5)
    for order in ([early, late], [late, early]):
        kept, dropped = drop_near_duplicates(order, [0, 0])
        assert kept == [early]
        assert dropped[0].highlight == late
        assert dropped[0].reason == "near_duplicate_of:a@1.000"


def test_nothing_disappears_and_max_distance_is_respected() -> None:
    hs = [_h("a", 0.0, 0.9), _h("b", 0.0, 0.8), _h("c", 0.0, 0.7)]
    kept, dropped = drop_near_duplicates(hs, [0b0, 0b1, 0b111], max_distance=1)
    assert kept == [hs[0], hs[2]]
    assert len(kept) + len(dropped) == len(hs)
    assert drop_near_duplicates(hs, [0b0, 0b1, 0b111], max_distance=0) == (hs, [])
    with pytest.raises(ValueError, match="same length"):
        drop_near_duplicates(hs, [0])
