"""Fotokarussell aus Bildern (SIN-1363): einheitliche 4:5-Slides, Cover, Manifest.

Deterministisch, nur FFmpeg. Text wird nicht ins Bild geschrieben; Captions stehen im Manifest.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from socialmedia_worker.dedupe import MAX_DISTANCE, frame_hash, hamming
from socialmedia_worker.quality import image_quality
from socialmedia_worker.render import COVER_TIMEOUT_S, RenderError, _run_ffmpeg
from socialmedia_worker.validate import validate_media

WIDTH, HEIGHT = 1080, 1350  # 4:5
MIN_SLIDES, MAX_SLIDES = 2, 10  # 10 = Instagram-Grenze (Annahme aus SIN-1363)
MANIFEST_VERSION = 1
MANIFEST_NAME = "carousel-manifest.v1.json"
PIPELINE_VERSION = "carousel-1"
APPROVAL_STATE = "wartet_auf_freigabe"
# Ganzes Bild einpassen und mit Schwarz auffüllen: nichts wird abgeschnitten.
_SLIDE_FILTER = (
    f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
    f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1"
)
_SLIDE_KEYS = {"position", "file", "asset_id", "sha256", "caption", "rationale"}
_OMITTED_KEYS = {"asset_id", "sha256", "reason"}


class CarouselError(ValueError):
    """Aus der Eingabe wird kein Karussell (zu wenige verschiedene Bilder)."""


@dataclass(frozen=True)
class CarouselResult:
    slides: list[Path]
    cover: Path
    manifest: Path


def _check_slide(path: Path) -> None:
    media = validate_media(path)
    if (media.kind, media.width, media.height) != ("image", WIDTH, HEIGHT):
        raise RenderError(f"slide is not a {WIDTH}x{HEIGHT} image: {path.name}")


def build_carousel(
    images: Mapping[str, Path],
    order: Sequence[str] | None = None,
    captions: Mapping[str, str] | None = None,
    *,
    out_dir: Path,
    max_distance: int = MAX_DISTANCE,
) -> CarouselResult:
    """Write slide-NN.jpg (1080x1350) and the manifest into the new folder `out_dir`.

    `images` maps asset ID to file. Without `order` the best picture comes first (no quality
    warning, then sharpness + exposure); with `order` exactly those IDs in that order. Near
    duplicates and everything beyond 10 slides are listed under `omitted` with a reason.
    Originals are only read. Fewer than 2 usable pictures: CarouselError, nothing is written.
    """
    captions = captions or {}
    unknown = sorted((set(order or ()) | set(captions)) - set(images))
    if unknown or (order is not None and len(set(order)) != len(order)):
        raise ValueError(f"order/captions: unbekannt oder doppelt: {unknown}")

    sha: dict[str, str] = {}
    note: dict[str, str] = {}
    score: dict[str, tuple[int, float]] = {}
    for asset_id in sorted(images):
        q = image_quality(images[asset_id])  # validiert: lesbares JPEG/PNG, kein Video
        sha[asset_id] = validate_media(images[asset_id]).sha256
        note[asset_id] = f"Schärfe {q.sharpness:.2f}, Belichtung {q.exposure:.2f}" + "".join(
            f", {r}" for r in q.reasons
        )
        score[asset_id] = (len(q.reasons), -(q.sharpness + q.exposure))
    if order is None:
        ranked = sorted(images, key=lambda a: (score[a], a))
        how = "nach Bildqualität"
    else:
        ranked = list(order)
        how = "manuelle Reihenfolge"

    omitted = {a: "nicht_in_reihenfolge" for a in images if a not in ranked}
    hashes = {a: frame_hash(images[a]) for a in ranked}
    chosen: list[str] = []
    for a in ranked:
        twin = next((c for c in chosen if hamming(hashes[a], hashes[c]) <= max_distance), None)
        if twin is not None:
            omitted[a] = f"near_duplicate_of:{twin}"
        elif len(chosen) == MAX_SLIDES:
            omitted[a] = f"ueber_limit:{MAX_SLIDES}"
        else:
            chosen.append(a)
    if len(chosen) < MIN_SLIDES:
        raise CarouselError(
            f"kein Karussell: {len(chosen)} verwendbares Bild von {len(images)}, "
            f"ein Karussell braucht mindestens {MIN_SLIDES} verschiedene Bilder"
        )

    out_dir.mkdir(parents=True)  # FileExistsError: ein früheres Karussell bleibt unangetastet
    try:
        slides = [out_dir / f"slide-{i:02d}.jpg" for i in range(1, len(chosen) + 1)]
        for asset_id, slide in zip(chosen, slides, strict=True):
            _run_ffmpeg(
                ["-i", str(images[asset_id]), "-frames:v", "1", "-vf", _SLIDE_FILTER, "-q:v", "2"],
                slide,
                COVER_TIMEOUT_S,
                _check_slide,
            )
        data = {
            "version": MANIFEST_VERSION,
            "pipeline_version": PIPELINE_VERSION,
            "approval_state": APPROVAL_STATE,
            "cover": slides[0].name,
            "slides": [
                {
                    "position": i,
                    "file": slide.name,
                    "asset_id": a,
                    "sha256": sha[a],
                    "caption": captions.get(a),
                    "rationale": f"Platz {i} {how}: {note[a]}",
                }
                for i, (a, slide) in enumerate(zip(chosen, slides, strict=True), start=1)
            ],
            "omitted": [
                {"asset_id": a, "sha256": sha[a], "reason": omitted[a]} for a in sorted(omitted)
            ],
        }
        validate_carousel(data)
        manifest = out_dir / MANIFEST_NAME
        manifest.write_text(
            json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
    except BaseException:
        shutil.rmtree(out_dir, ignore_errors=True)  # von diesem Aufruf angelegt
        raise
    return CarouselResult(slides, slides[0], manifest)


def validate_carousel(data: dict[str, Any]) -> None:
    """Feldprüfung wie ``schemas/carousel.v1.json`` (kein Schema-Paket im Lockfile)."""
    keys = {"version", "pipeline_version", "approval_state", "cover", "slides", "omitted"}
    if set(data) != keys or data["version"] != MANIFEST_VERSION:
        raise ValueError("carousel: wrong keys or version")
    if data["approval_state"] != APPROVAL_STATE:
        raise ValueError("carousel: approval_state")
    if not isinstance(data["pipeline_version"], str) or not data["pipeline_version"]:
        raise ValueError("carousel: pipeline_version")
    slides, omitted = data["slides"], data["omitted"]
    if not isinstance(slides, list) or not MIN_SLIDES <= len(slides) <= MAX_SLIDES:
        raise ValueError(f"carousel: need {MIN_SLIDES}..{MAX_SLIDES} slides")
    for i, s in enumerate(slides, start=1):
        if not isinstance(s, dict) or set(s) != _SLIDE_KEYS or s["position"] != i:
            raise ValueError("carousel: slide keys or position")
        if not (s["caption"] is None or isinstance(s["caption"], str)):
            raise ValueError("carousel: caption")
    if data["cover"] != slides[0]["file"]:
        raise ValueError("carousel: cover must be the first slide")
    if not isinstance(omitted, list) or any(
        not isinstance(o, dict) or set(o) != _OMITTED_KEYS for o in omitted
    ):
        raise ValueError("carousel: omitted")
    for entry in [*slides, *omitted]:
        for key in set(entry) - {"position", "caption"}:
            if not isinstance(entry[key], str) or not entry[key]:
                raise ValueError(f"carousel: {key}")
        if len(entry["sha256"]) != 64:
            raise ValueError("carousel: sha256")
