"""Automatische Highlights gegen menschliche Markierungen auswerten (SIN-1375).

Reine Rechnung auf zwei JSON-Dateien, ohne FFmpeg. Vorgehen und Grenzen: ``docs/EVAL.md``.
"""

from __future__ import annotations

from typing import Any

from socialmedia_worker.pipeline import validate_analysis

LABELS_VERSION = 1
REPORT_VERSION = 1
IOU_MIN = 0.5
MIN_LABELS = 10  # darunter trägt der Bericht die Warnung
WARNUNG = "zu klein für Aussagen"

Range = tuple[float, float]


def iou(a: Range, b: Range) -> float:
    """Überlappung zweier Zeitbereiche geteilt durch ihre Vereinigung (0..1)."""
    inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    union = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / union if union > 0 else 0.0


def validate_labels(data: dict[str, Any]) -> None:
    """Feldprüfung wie ``schemas/labels.v1.json`` (kein Schema-Paket im Lockfile)."""
    if set(data) != {"version", "asset_id", "labels"} or data["version"] != LABELS_VERSION:
        raise ValueError("labels: wrong keys or version")
    if not isinstance(data["asset_id"], str) or not data["asset_id"]:
        raise ValueError("labels: asset_id")
    if not isinstance(data["labels"], list):
        raise ValueError("labels: labels must be a list")
    for label in data["labels"]:
        if not isinstance(label, dict) or not {"start", "end"} <= set(label) <= {
            "start", "end", "note",
        }:
            raise ValueError("labels: label keys")
        for key in ("start", "end"):
            if isinstance(label[key], bool) or not isinstance(label[key], int | float):
                raise ValueError(f"labels: {key} must be a number")
        if not 0 <= label["start"] < label["end"]:
            raise ValueError("labels: require 0 <= start < end")
        if not isinstance(label.get("note", ""), str):
            raise ValueError("labels: note")


def _ratio(part: int, whole: int) -> float | None:
    return round(part / whole, 4) if whole else None


def evaluate(
    labels: dict[str, Any], analysis: dict[str, Any], iou_min: float = IOU_MIN
) -> dict[str, Any]:
    """Compare the highlights of one analysis (analysis.v1) with human labels (labels.v1).

    A highlight is a hit when its IoU with a not yet matched label is >= iou_min; highlights are
    matched in order of confidence and each label counts once. precision/recall are None when
    there is nothing to divide by. saved_seconds = raw material minus the highlights a human
    still has to watch; it says nothing about whether the right moments were found.
    """
    if not 0 < iou_min <= 1:
        raise ValueError("iou_min must be in (0, 1]")
    validate_labels(labels)
    validate_analysis(analysis)
    if labels["asset_id"] != analysis["asset_id"]:
        raise ValueError("asset_id of labels and analysis differ")
    if analysis["kind"] != "video" or analysis["duration"] is None:
        raise ValueError("analysis: nur ein Video lässt sich auswerten")

    open_labels: list[Range] = [(float(x["start"]), float(x["end"])) for x in labels["labels"]]
    highlights = sorted(analysis["highlights"], key=lambda h: (-h["confidence"], h["start"]))
    hits = 0
    for h in highlights:
        span = (float(h["start"]), float(h["end"]))
        best = max(open_labels, key=lambda label: iou(span, label), default=None)
        if best is not None and iou(span, best) >= iou_min:
            open_labels.remove(best)
            hits += 1
    raw = float(analysis["duration"])
    review = sum(float(h["end"]) - float(h["start"]) for h in highlights)
    n_labels = len(labels["labels"])
    return {
        "version": REPORT_VERSION,
        "asset_id": analysis["asset_id"],
        "pipeline_version": analysis["pipeline_version"],
        "iou_min": iou_min,
        "labels": n_labels,
        "highlights": len(highlights),
        "hits": hits,
        "false_positives": len(highlights) - hits,
        "missed": n_labels - hits,
        "precision": _ratio(hits, len(highlights)),
        "recall": _ratio(hits, n_labels),
        "raw_seconds": round(raw, 3),
        "review_seconds": round(review, 3),
        "saved_seconds": round(raw - review, 3),
        "warning": WARNUNG if n_labels < MIN_LABELS else None,
    }


def to_markdown(report: dict[str, Any]) -> str:
    def cell(value: float | None) -> str:
        return "–" if value is None else f"{value:.2f}"

    rows = [
        ("Labels (Mensch)", str(report["labels"])),
        ("Highlights (automatisch)", str(report["highlights"])),
        (f"Treffer (IoU >= {report['iou_min']})", str(report["hits"])),
        ("Fehltreffer", str(report["false_positives"])),
        ("Verpasst", str(report["missed"])),
        ("Precision", cell(report["precision"])),
        ("Recall", cell(report["recall"])),
        ("Rohmaterial (s)", f"{report['raw_seconds']:.1f}"),
        ("Zu prüfen (s)", f"{report['review_seconds']:.1f}"),
        ("Gespart (s)", f"{report['saved_seconds']:.1f}"),
    ]
    lines = [f"| Kennzahl | {report['asset_id']} |", "| --- | --- |"]
    lines += [f"| {name} | {value} |" for name, value in rows]
    if report["warning"]:
        lines += ["", f"Warnung: {report['labels']} Labels, {report['warning']}."]
    return "\n".join(lines)
