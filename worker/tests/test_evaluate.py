import json
from pathlib import Path
from typing import Any

import pytest

from socialmedia_worker.__main__ import main
from socialmedia_worker.evaluate import evaluate, iou, to_markdown, validate_labels

HERE = Path(__file__).parent
BEISPIEL = HERE / "data" / "labels.beispiel.json"
SCHEMA = HERE.parent / "schemas" / "labels.v1.json"
WARNUNG = "zu klein für Aussagen"


def _analysis(highlights: list[tuple[float, float, float]], duration: float = 120.0) -> Any:
    return {
        "version": 1,
        "asset_id": "asset-1",
        "kind": "video",
        "sha256": "0" * 64,
        "duration": duration,
        "width": 1920,
        "height": 1080,
        "segments": [],
        "highlights": [
            {"asset_id": "asset-1", "start": s, "end": e, "confidence": c,
             "rationale": "Test", "pipeline_version": "test-1"}
            for s, e, c in highlights
        ],
        "quality": None,
        "pipeline_version": "test-1",
    }


def _labels(ranges: list[tuple[float, float]]) -> Any:
    return {
        "version": 1,
        "asset_id": "asset-1",
        "labels": [{"start": s, "end": e} for s, e in ranges],
    }


def test_iou_by_hand() -> None:
    assert iou((0, 10), (0, 10)) == 1.0
    assert iou((0, 10), (5, 15)) == pytest.approx(5 / 15)
    assert iou((0, 10), (10, 20)) == 0.0


def test_precision_and_recall_by_hand() -> None:
    labels = json.loads(BEISPIEL.read_text(encoding="utf-8"))  # 0-10, 20-30, 50-60
    # 0-8: IoU 8/10 = 0,8 → Treffer. 24-34: IoU 6/14 ≈ 0,43 → Fehltreffer. 80-90: kein Label.
    report = evaluate(labels, _analysis([(0, 8, 0.9), (24, 34, 0.8), (80, 90, 0.7)]))
    assert (report["hits"], report["false_positives"], report["missed"]) == (1, 2, 2)
    assert report["precision"] == pytest.approx(1 / 3, abs=1e-4)
    assert report["recall"] == pytest.approx(1 / 3, abs=1e-4)
    # Gesparte Zeit: 120 s Rohmaterial, 8 + 10 + 10 = 28 s Highlights zu prüfen.
    assert (report["raw_seconds"], report["review_seconds"], report["saved_seconds"]) == (
        120.0, 28.0, 92.0,
    )
    assert report["iou_min"] == 0.5
    # Schwelle konfigurierbar: mit 0,4 zählt 24-34 als Treffer.
    loose = evaluate(labels, _analysis([(0, 8, 0.9), (24, 34, 0.8), (80, 90, 0.7)]), iou_min=0.4)
    assert (loose["hits"], loose["false_positives"], loose["missed"]) == (2, 1, 1)


def test_a_label_counts_only_once() -> None:
    # Zwei Highlights auf demselben Label: ein Treffer, ein Fehltreffer.
    report = evaluate(_labels([(0, 10)]), _analysis([(0, 10, 0.5), (1, 10, 0.9)]))
    assert (report["hits"], report["false_positives"], report["missed"]) == (1, 1, 0)
    assert report["precision"] == 0.5 and report["recall"] == 1.0


def test_no_labels_and_no_highlights_do_not_divide_by_zero() -> None:
    none = evaluate(_labels([]), _analysis([]))
    assert none["precision"] is None and none["recall"] is None
    assert none["saved_seconds"] == 120.0
    only_highlights = evaluate(_labels([]), _analysis([(0, 5, 0.5)]))
    assert only_highlights["precision"] == 0.0 and only_highlights["recall"] is None
    only_labels = evaluate(_labels([(0, 5)]), _analysis([]))
    assert only_labels["precision"] is None and only_labels["recall"] == 0.0


def test_small_sample_carries_the_warning() -> None:
    small = evaluate(_labels([(i * 10.0, i * 10.0 + 5) for i in range(9)]), _analysis([]))
    assert small["warning"] == WARNUNG
    assert WARNUNG in to_markdown(small)
    enough = evaluate(_labels([(i * 10.0, i * 10.0 + 5) for i in range(10)]), _analysis([]))
    assert enough["warning"] is None
    assert WARNUNG not in to_markdown(enough)


def test_rejects_bad_input() -> None:
    with pytest.raises(ValueError, match="asset_id"):
        evaluate({**_labels([]), "asset_id": "anderes"}, _analysis([]))
    with pytest.raises(ValueError, match="start < end"):
        validate_labels(_labels([(5, 5)]))
    with pytest.raises(ValueError, match="version"):
        validate_labels({**_labels([]), "version": 2})
    with pytest.raises(ValueError, match="Video"):
        evaluate(_labels([]), {**_analysis([]), "kind": "image", "duration": None})
    with pytest.raises(ValueError, match="iou_min"):
        evaluate(_labels([]), _analysis([]), iou_min=0)


def test_example_matches_the_schema_file() -> None:
    labels = json.loads(BEISPIEL.read_text(encoding="utf-8"))
    validate_labels(labels)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert set(schema["required"]) == set(labels) == {"version", "asset_id", "labels"}
    assert schema["properties"]["version"]["const"] == labels["version"]
    item = schema["properties"]["labels"]["items"]
    assert set(item["required"]) == {"start", "end"}
    assert set(item["properties"]) == {"start", "end", "note"}


def test_cli_prints_json_or_markdown(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    analysis = tmp_path / "analysis.json"
    analysis.write_text(json.dumps(_analysis([(0, 8, 0.9)])), encoding="utf-8")
    args = ["evaluate", "--labels", str(BEISPIEL), "--analysis", str(analysis)]
    assert main(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["hits"] == 1 and report["warning"] == WARNUNG
    assert main([*args, "--markdown", "--iou", "0.9"]) == 0
    table = capsys.readouterr().out
    assert "| Precision |" in table and WARNUNG in table
    table.encode("cp1252")  # Windows-Konsole: sonst bricht print mit UnicodeEncodeError ab
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    assert main(["evaluate", "--labels", str(bad), "--analysis", str(analysis)]) == 2
    assert "labels" in capsys.readouterr().err
