import json
import shutil
from pathlib import Path

import pytest

from socialmedia_worker.__main__ import main
from socialmedia_worker.checkpoints import (
    Artefakt,
    Checkpoint,
    JsonlReporter,
    MultiReporter,
    auftrag_sql,
    insert_sql,
)
from socialmedia_worker.pipeline import (
    analyze_asset,
    beispiel,
    export_batch,
    run_batch,
    validate_analysis,
)

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg fehlt")


@pytest.fixture(scope="module")
def material(tmp_path_factory: pytest.TempPathFactory) -> list[Path]:
    return beispiel(tmp_path_factory.mktemp("material"))


def test_analyze_asset_is_deterministic_and_valid(material: list[Path]) -> None:
    a = analyze_asset(material[0], "asset-1")
    b = analyze_asset(material[0], "asset-1")
    assert a.to_json() == b.to_json()
    data = json.loads(a.to_json())
    validate_analysis(data)
    assert data["kind"] == "video" and len(data["highlights"]) >= 2
    bild = analyze_asset(material[2], "asset-3")
    validate_analysis(json.loads(bild.to_json()))
    assert bild.kind == "image" and bild.quality is not None and bild.highlights == []


def test_batch_runs_to_freigabe_and_export_waits_for_decision(
    material: list[Path], tmp_path: Path
) -> None:
    out = tmp_path / "lauf"
    reporter = JsonlReporter(out / "checkpoints.jsonl")
    quellen = {p.name: p.read_bytes() for p in material}
    manifest = run_batch(material, out, "pilot-test", reporter)
    assert {p.name: p.read_bytes() for p in material} == quellen, "Originale bleiben byteidentisch"
    assert len(manifest["varianten"]) == 2 and all(p["ok"] for p in manifest["pruefungen"])
    for v in manifest["varianten"]:
        assert (out / v["video"]).stat().st_size > 0 and (out / v["cover"]).stat().st_size > 0
    zeilen = [
        json.loads(z) for z in (out / "checkpoints.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert zeilen[0]["schritte"][0] == "Upload"
    assert [(z["schritt"], z["status"]) for z in zeilen[1:]] == [
        ("Upload", "fertig"),
        ("Highlights", "fertig"),
        ("Videoschnitt", "fertig"),
        ("Qualitätsprüfung", "fertig"),
        ("Freigabe", "blockiert"),
    ]
    assert zeilen[3]["artefakte"][0]["url"] == "/artefakt/pilot-test/variante-1.mp4"
    assert zeilen[5]["entscheidung"]
    assert export_batch(out, "pilot-test", reporter) is None, "ohne Entscheidung kein Export"
    assert main(["export", "--out", str(out), "--auftrag", "pilot-test"]) == 3
    reporter.checkpoint(
        Checkpoint(
            "pilot-test",
            "Freigabe",
            "fertig",
            "Sinan (Cockpit)",
            "Cockpit",
            [],
            ergebnis="freigegeben",
        )
    )
    ziel = export_batch(out, "pilot-test", reporter)
    assert ziel is not None and (ziel / "variante-2.mp4").exists()
    export = json.loads((ziel / "export.json").read_text(encoding="utf-8"))
    assert export["freigabe"] == "freigegeben" and len(export["dateien"]) == 4
    assert (
        json.loads((out / "checkpoints.jsonl").read_text(encoding="utf-8").splitlines()[-1])[
            "schritt"
        ]
        == "Export"
    )


def test_batch_without_video_fails_at_upload(material: list[Path], tmp_path: Path) -> None:
    out = tmp_path / "nur-bild"
    with pytest.raises(SystemExit) as e:
        run_batch([material[2]], out, "pilot-bild", JsonlReporter(out / "checkpoints.jsonl"))
    assert e.value.code == 2
    letzte = json.loads((out / "checkpoints.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert (letzte["schritt"], letzte["status"]) == (
        "Upload",
        "fehlgeschlagen",
    ) and "kein gültiges Video" in letzte["fehler"]


def test_rejected_file_gives_exit_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "bad.mp4"
    bad.write_bytes(b"not a video")
    assert main(["analyze", str(bad), "--asset-id", "x"]) == 2
    assert "reason" in capsys.readouterr().err
    assert bad.read_bytes() == b"not a video"


def test_sql_literals_and_freigabe_order() -> None:
    cp = Checkpoint(
        "p",
        "Freigabe",
        "fertig",
        "Sinan's",
        "pc",
        ["a"],
        artefakte=[Artefakt("datei", "x", "/artefakt/p/x")],
        entscheidung="Ok?",
    )
    s = insert_sql(cp)
    assert (
        "'Sinan''s'" in s
        and "array['a']::text[]" in s
        and '"url": "/artefakt/p/x"' in s
        and s.endswith(", 1, 'Ok?')")
    )
    assert "on conflict (id) do nothing" in auftrag_sql("p", "t")
    with pytest.raises(ValueError):
        insert_sql(Checkpoint("p", "s", "fertig", "a\0b", "pc", []))
    erst = JsonlReporter(Path("nicht-da.jsonl"))
    assert MultiReporter([erst]).freigabe("p") is None
