import json
import math
from dataclasses import asdict, dataclass
from typing import Any

PIPELINE_VERSION = "highlights-heuristic-1"
MANIFEST_VERSION = 1


@dataclass(frozen=True)
class Highlight:
    asset_id: str
    start: float
    end: float
    confidence: float
    rationale: str
    pipeline_version: str


@dataclass(frozen=True)
class Manifest:
    asset_id: str
    highlights: list[Highlight]

    def to_json(self) -> str:
        """Deterministic JSON (sorted keys); schema: schemas/highlights.v1.json."""
        data = {
            "version": MANIFEST_VERSION,
            "asset_id": self.asset_id,
            "highlights": [asdict(h) for h in self.highlights],
        }
        return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def select_highlights(
    asset_id: str,
    segments: list[tuple[float, float]],
    signals: list[float],
    min_len: float,
    max_len: float,
    top_n: int,
) -> Manifest:
    """Rank scene segments by a per-segment signal (e.g. motion, 0..1) and keep the top_n.

    Segments shorter than min_len are dropped; longer than max_len are cut to their first
    max_len seconds. confidence is the signal clamped to 0..1: a heuristic, not a prediction
    of reach or virality. Ties are broken by earlier start.
    """
    if len(segments) != len(signals):
        raise ValueError("segments and signals must have the same length")
    if not 0 < min_len <= max_len:
        raise ValueError("require 0 < min_len <= max_len")
    if top_n < 1:
        raise ValueError("top_n must be >= 1")
    candidates: list[Highlight] = []
    for (start, end), signal in zip(segments, signals, strict=True):
        if not (math.isfinite(signal) and 0 <= start < end):
            raise ValueError(f"invalid segment or signal: ({start}, {end}), {signal}")
        length = end - start
        if length < min_len:
            continue
        confidence = round(min(max(signal, 0.0), 1.0), 4)
        rationale = f"Signalwert {signal:.2f} (Heuristik), Segment {length:.1f} s"
        if length > max_len:
            end = start + max_len
            rationale += f", auf {max_len:.1f} s gekürzt"
        candidates.append(
            Highlight(asset_id, float(start), float(end), confidence, rationale, PIPELINE_VERSION)
        )
    candidates.sort(key=lambda h: (-h.confidence, h.start))
    return Manifest(asset_id, candidates[:top_n])


def validate_manifest(data: dict[str, Any]) -> None:
    """Field check mirroring schemas/highlights.v1.json (no schema package in the lockfile)."""
    if set(data) != {"version", "asset_id", "highlights"} or data["version"] != MANIFEST_VERSION:
        raise ValueError("manifest: wrong keys or version")
    if not isinstance(data["asset_id"], str) or not data["asset_id"]:
        raise ValueError("manifest: asset_id")
    if not isinstance(data["highlights"], list):
        raise ValueError("manifest: highlights must be a list")
    for h in data["highlights"]:
        if not isinstance(h, dict) or set(h) != set(Highlight.__annotations__):
            raise ValueError("highlight: wrong keys")
        for key in ("asset_id", "rationale", "pipeline_version"):
            if not isinstance(h[key], str) or not h[key]:
                raise ValueError(f"highlight: {key}")
        for key in ("start", "end", "confidence"):
            if isinstance(h[key], bool) or not isinstance(h[key], int | float):
                raise ValueError(f"highlight: {key} must be a number")
        if not 0 <= h["start"] < h["end"]:
            raise ValueError("highlight: require 0 <= start < end")
        if not 0 <= h["confidence"] <= 1:
            raise ValueError("highlight: confidence outside 0..1")
