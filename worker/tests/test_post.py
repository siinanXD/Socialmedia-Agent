import json
import shutil
from pathlib import Path

import pytest

from socialmedia_worker.highlights import Highlight
from socialmedia_worker.pipeline import beispiel
from socialmedia_worker.post import (
    CLIP_S,
    FOTO_S,
    UEBERGANG_S,
    ZIEL_MAX_S,
    Baustein,
    baue_storyboards,
    lautheit,
    render_post,
)
from socialmedia_worker.probe import probe


def _h(asset: str, start: float, confidence: float, laenge: float = 6.0) -> Highlight:
    return Highlight(asset, start, start + laenge, confidence, "r", "p")


QUELLEN = {"a": "a.mp4", "b": "b.mp4"}
KANDIDATEN = [_h("a", 6, 0.9), _h("b", 12, 0.6), _h("a", 0, 0.5), _h("b", 0, 0.3)]


def test_hook_zuerst_und_chronologisch_unterscheiden_sich() -> None:
    boards = baue_storyboards(KANDIDATEN, QUELLEN, ["f1.jpg", "f2.jpg"])
    assert [b.strategie for b in boards] == ["hook", "chronologisch"]
    hook, chrono = boards
    assert (hook.bausteine[0].quelle, hook.bausteine[0].start) == ("a.mp4", 6)
    assert hook.bausteine[1].quelle == "b.mp4", "zweiter Clip aus dem anderen Video"
    assert (chrono.bausteine[0].quelle, chrono.bausteine[0].start) == ("a.mp4", 0)
    assert all(b.art == "foto" and b.dauer == FOTO_S for b in hook.bausteine if b.quelle[0] == "f")
    assert all(b.dauer <= CLIP_S for b in hook.bausteine)


def test_dauer_rechnet_uebergaenge_ab_und_bleibt_unter_dem_ziel() -> None:
    viele = [_h("a", float(i * 6), 0.9 - i / 100) for i in range(20)]
    b = baue_storyboards(viele, {"a": "a.mp4"}, [])[0]
    n = len(b.bausteine)
    assert b.dauer == pytest.approx(sum(x.dauer for x in b.bausteine) - (n - 1) * UEBERGANG_S)
    assert b.dauer <= ZIEL_MAX_S
    orte = [(x.quelle, x.start) for x in b.bausteine]
    assert len(orte) == len(set(orte)), "kein Quellbereich doppelt"


def test_gleiche_folge_ergibt_nur_eine_variante_und_leer_ergibt_keine() -> None:
    assert len(baue_storyboards([_h("a", 0, 0.5)], {"a": "a.mp4"}, [])) == 1
    assert baue_storyboards([], {}, []) == []
    a = json.dumps([b.to_dict() for b in baue_storyboards(KANDIDATEN, QUELLEN, ["f.jpg"])])
    assert a == json.dumps([b.to_dict() for b in baue_storyboards(KANDIDATEN, QUELLEN, ["f.jpg"])])


def test_kurzes_highlight_wird_nicht_verlaengert() -> None:
    b = baue_storyboards([_h("a", 0, 0.5, laenge=2.0)], {"a": "a.mp4"}, [])[0]
    assert b.bausteine == [Baustein("video", "a.mp4", 0.0, 2.0, 0.5)]


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg fehlt")
def test_render_post_ergibt_ein_video_aus_mehreren_quellen(tmp_path: Path) -> None:
    m = beispiel(tmp_path / "m")
    quellen = {p.name: p for p in m}
    vorher = {p.name: p.read_bytes() for p in m}
    k = [_h("clip-a.mp4", 0, 0.9, 3.0), _h("clip-b.mp4", 0, 0.8, 3.0)]
    board = baue_storyboards(k, {h.asset_id: h.asset_id for h in k}, ["foto.png"])[0]
    assert [b.art for b in board.bausteine] == ["video", "video", "foto"]
    ziel = tmp_path / "post.mp4"
    render_post(board, quellen, ziel)
    p = probe(ziel)
    assert (p.width, p.height) == (1080, 1920)
    assert p.duration == pytest.approx(board.dauer, abs=0.3)
    assert lautheit(ziel) == pytest.approx(-14.0, abs=1.0)
    assert {p.name: p.read_bytes() for p in m} == vorher, "Quellen bleiben byteidentisch"
    assert not list(tmp_path.glob(".*")), "keine Zwischendatei bleibt liegen"
    with pytest.raises(FileExistsError):
        render_post(board, quellen, ziel)
