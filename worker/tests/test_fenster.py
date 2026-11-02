import shutil
import subprocess
from pathlib import Path

import pytest

from socialmedia_worker.highlights import Highlight
from socialmedia_worker.pipeline import FENSTER_S, analyze_asset, in_fenster
from socialmedia_worker.post import waehle_varianten


def test_in_fenster_teilt_lange_aufnahmen_und_haengt_kurzen_rest_an() -> None:
    assert in_fenster([(0.0, 4.0)]) == [(0.0, 4.0)], "kurze Szene bleibt ganz"
    assert in_fenster([(0.0, 18.0)]) == [(0.0, 6.0), (6.0, 12.0), (12.0, 18.0)]
    assert in_fenster([(0.0, 14.13)]) == [(0.0, 6.0), (6.0, 14.13)], "Rest unter 3 s kommt ans Ende"
    assert in_fenster([(1.0, 3.0), (3.0, 16.0)]) == [(1.0, 3.0), (3.0, 9.0), (9.0, 16.0)]


def _h(asset: str, start: float, confidence: float) -> Highlight:
    return Highlight(asset, start, start + FENSTER_S, confidence, "r", "p")


def test_waehle_varianten_nimmt_erst_das_beste_je_asset() -> None:
    k = [_h("a", 0, 0.9), _h("a", 6, 0.8), _h("b", 0, 0.4)]
    assert [(h.asset_id, h.start) for h in waehle_varianten(k, 2)] == [("a", 0), ("b", 0)]
    assert [(h.asset_id, h.start) for h in waehle_varianten(k[:2], 2)] == [("a", 0), ("a", 6)]


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg fehlt")
def test_durchgehende_aufnahme_ergibt_kuerzere_highlights(tmp_path: Path) -> None:
    clip = tmp_path / "eine-aufnahme.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-nostdin", "-y", "-f", "lavfi", "-i",
         "testsrc2=duration=14:size=320x240:rate=25", "-pix_fmt", "yuv420p", str(clip)],
        check=True,
    )  # fmt: skip
    a = analyze_asset(clip, "a1")
    assert len(a.segments) == 2 and a.highlights
    assert all(h.end - h.start < 14 for h in a.highlights), "nicht der ganze Clip"
