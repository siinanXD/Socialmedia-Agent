import json
from pathlib import Path

import pytest

from socialmedia_worker.highlights import PIPELINE_VERSION, select_highlights, validate_manifest

SCHEMA = Path(__file__).parent.parent / "schemas" / "highlights.v1.json"
SEGMENTS = [(0.0, 2.0), (2.0, 10.0), (10.0, 14.0), (14.0, 30.0)]
SIGNALS = [0.9, 0.2, 0.7, 0.5]


def test_ranking_truncation_and_drop() -> None:
    m = select_highlights("a1", SEGMENTS, SIGNALS, min_len=3.0, max_len=6.0, top_n=2)
    # (0,2) is shorter than min_len -> dropped; (14,30) -> cut to (14,20)
    assert [(h.start, h.end) for h in m.highlights] == [(10.0, 14.0), (14.0, 20.0)]
    assert [h.confidence for h in m.highlights] == [0.7, 0.5]
    assert all(h.asset_id == "a1" and h.pipeline_version == PIPELINE_VERSION for h in m.highlights)
    assert all(h.rationale for h in m.highlights)
    assert "gekürzt" in m.highlights[1].rationale


def test_confidence_is_clamped_and_ties_break_by_start() -> None:
    m = select_highlights("a", [(0, 4), (4, 8)], [1.7, 1.7], min_len=1, max_len=10, top_n=5)
    assert [h.confidence for h in m.highlights] == [1.0, 1.0]
    assert [h.start for h in m.highlights] == [0.0, 4.0]


def test_signal_count_mismatch_rejected() -> None:
    with pytest.raises(ValueError):
        select_highlights("a", SEGMENTS, [0.1], min_len=1, max_len=5, top_n=1)


def test_invalid_params_rejected() -> None:
    with pytest.raises(ValueError):
        select_highlights("a", SEGMENTS, SIGNALS, min_len=5, max_len=2, top_n=1)
    with pytest.raises(ValueError):
        select_highlights("a", SEGMENTS, SIGNALS, min_len=1, max_len=5, top_n=0)


def test_manifest_validates_against_schema() -> None:
    m = select_highlights("a1", SEGMENTS, SIGNALS, min_len=3.0, max_len=6.0, top_n=3)
    data = json.loads(m.to_json())
    schema = json.loads(SCHEMA.read_text())
    assert schema["properties"]["version"]["const"] == data["version"]
    validate_manifest(data)
    required = set(schema["properties"]["highlights"]["items"]["required"])
    assert all(set(h) == required for h in data["highlights"])


def test_validate_manifest_rejects_bad_data() -> None:
    m = select_highlights("a1", SEGMENTS, SIGNALS, min_len=3.0, max_len=6.0, top_n=1)
    data = json.loads(m.to_json())
    data["highlights"][0]["confidence"] = 1.5
    with pytest.raises(ValueError):
        validate_manifest(data)
    data["highlights"][0]["confidence"] = 0.5
    del data["highlights"][0]["rationale"]
    with pytest.raises(ValueError):
        validate_manifest(data)


def test_deterministic_bytes() -> None:
    a = select_highlights("a1", SEGMENTS, SIGNALS, min_len=3.0, max_len=6.0, top_n=3).to_json()
    b = select_highlights("a1", SEGMENTS, SIGNALS, min_len=3.0, max_len=6.0, top_n=3).to_json()
    assert a == b
