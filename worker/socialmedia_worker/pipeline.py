"""Pilot-Pipeline (SIN-1355, SIN-1364, SIN-1077).

Upload → Highlights → Videoschnitt → Qualitätsprüfung → Freigabe → Export.

Deterministisch, nur FFmpeg/ffprobe über die vorhandenen Bausteine (validate, scenes, signals,
highlights, render, quality). Kein Modell, keine Datenbank-Queue: die Strecke liest Dateien
und schreibt Artefakte plus einen Checkpoint je Schritt (``checkpoints.py``). Der Export läuft
erst, wenn im Checkpoint ``Freigabe`` eine Entscheidung steht (Cockpit oder JSONL).
"""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from socialmedia_worker.checkpoints import Artefakt, ArtefaktArt, Checkpoint, Reporter, Status
from socialmedia_worker.highlights import Highlight, select_highlights
from socialmedia_worker.probe import probe
from socialmedia_worker.quality import image_quality
from socialmedia_worker.render import extract_cover, render_vertical
from socialmedia_worker.scenes import detect_scenes, to_segments
from socialmedia_worker.signals import segment_signals
from socialmedia_worker.validate import MediaLimits, MediaRejectedError, validate_media

PIPELINE_VERSION = "pipeline-2"
ANALYSIS_VERSION = 1
AGENT = "socialmedia-worker (Python, deterministisch)"
MIN_LEN = 2.0
MAX_LEN = 30.0
VARIANTEN = 2
# shortcut: feste 6 s statt Inhaltserkennung, ersetzen, sobald echte Korrekturen vorliegen.
FENSTER_S = 6.0


def in_fenster(segmente: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Teilt lange Segmente in Fenster: Eine durchgehende Aufnahme hat keine Schnitte."""
    aus: list[tuple[float, float]] = []
    for start, ende in segmente:
        while ende - start >= FENSTER_S * 1.5:
            aus.append((start, start + FENSTER_S))
            start += FENSTER_S
        aus.append((start, ende))
    return aus


def waehle_varianten(kandidaten: list[Highlight], anzahl: int) -> list[Highlight]:
    """Erst das Beste je Asset, dann der Rest: Fenster derselben Aufnahme ähneln sich."""
    gesehen: set[str] = set()
    erste: list[Highlight] = []
    rest: list[Highlight] = []
    for h in kandidaten:
        (rest if h.asset_id in gesehen else erste).append(h)
        gesehen.add(h.asset_id)
    return (erste + rest)[:anzahl]


@dataclass(frozen=True)
class AnalysisResult:
    """Ergebnis von ``analyze_asset`` (Schema ``schemas/analysis.v1.json``)."""

    asset_id: str
    kind: str
    sha256: str
    duration: float | None
    width: int
    height: int
    segments: list[tuple[float, float]]
    highlights: list[Highlight]
    quality: dict[str, Any] | None
    pipeline_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": ANALYSIS_VERSION,
            "asset_id": self.asset_id,
            "kind": self.kind,
            "sha256": self.sha256,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "segments": [[s, e] for s, e in self.segments],
            "highlights": [asdict(h) for h in self.highlights],
            "quality": self.quality,
            "pipeline_version": self.pipeline_version,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def validate_analysis(data: dict[str, Any]) -> None:
    """Feldprüfung wie ``schemas/analysis.v1.json`` (kein Schema-Paket im Lockfile)."""
    keys = {
        "version",
        "asset_id",
        "kind",
        "sha256",
        "duration",
        "width",
        "height",
        "segments",
        "highlights",
        "quality",
        "pipeline_version",
    }
    if set(data) != keys or data["version"] != ANALYSIS_VERSION:
        raise ValueError("analysis: wrong keys or version")
    if data["kind"] not in ("video", "image"):
        raise ValueError("analysis: kind")
    if not isinstance(data["sha256"], str) or len(data["sha256"]) != 64:
        raise ValueError("analysis: sha256")
    for s in data["segments"]:
        if not (isinstance(s, list) and len(s) == 2 and 0 <= s[0] < s[1]):
            raise ValueError("analysis: segment")
    for h in data["highlights"]:
        if set(h) != set(Highlight.__annotations__) or not 0 <= h["start"] < h["end"]:
            raise ValueError("analysis: highlight")


def analyze_asset(
    path: Path, asset_id: str, limits: MediaLimits | None = None, top_n: int = 3
) -> AnalysisResult:
    """Eine Datei: validate → (Video: Szenen → Signale → Highlights | Bild: Qualität). Liest nur."""
    media = validate_media(path, limits)
    if media.kind == "image":
        q = image_quality(path)
        return AnalysisResult(
            asset_id,
            "image",
            media.sha256,
            None,
            media.width,
            media.height,
            [],
            [],
            asdict(q),
            PIPELINE_VERSION,
        )
    duration = media.duration or probe(path).duration
    segments = in_fenster(to_segments(detect_scenes(path), duration))
    signals = [s.motion for s in segment_signals(path, segments)]
    manifest = select_highlights(
        asset_id, segments, signals, MIN_LEN, min(MAX_LEN, duration), top_n
    )
    return AnalysisResult(
        asset_id,
        "video",
        media.sha256,
        duration,
        media.width,
        media.height,
        segments,
        manifest.highlights,
        None,
        PIPELINE_VERSION,
    )


@dataclass(frozen=True)
class Variante:
    name: str
    asset_id: str
    quelle: str
    start: float
    end: float
    confidence: float
    video: str
    cover: str


@dataclass(frozen=True)
class Pruefung:
    name: str
    ok: bool
    befund: str


def pruefe_variante(out: Path, v: Variante) -> Pruefung:
    """Abnahme der Datei: 1080×1920, Dauer wie geplant (±0,5 s), Cover ist ein Bild."""
    gruende: list[str] = []
    video = out / v.video
    try:
        p = probe(video)
        if (p.width, p.height) != (1080, 1920):
            gruende.append(f"Format {p.width}x{p.height} statt 1080x1920")
        if abs(p.duration - (v.end - v.start)) > 0.5:
            gruende.append(f"Dauer {p.duration:.2f} s statt {v.end - v.start:.2f} s")
        if video.stat().st_size == 0:
            gruende.append("Datei leer")
    except Exception as err:  # ffprobe-Fehler ist ein Befund, kein Absturz
        gruende.append(f"ffprobe: {err}")
    try:
        if validate_media(out / v.cover).kind != "image":
            gruende.append("Cover ist kein Bild")
    except MediaRejectedError as err:
        gruende.append(f"Cover: {err}")
    return Pruefung(
        v.name, not gruende, "; ".join(gruende) or f"1080x1920, {v.end - v.start:.1f} s, Cover ok"
    )


def _werkzeuge() -> list[str]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return ["ffmpeg fehlt"]
    out = subprocess.run(
        [ffmpeg, "-version"], capture_output=True, text=True, check=False
    ).stdout.splitlines()
    return [out[0].split(" Copyright")[0] if out else "ffmpeg", "ffprobe"]


class Lauf:
    """Ein Batch-Lauf: Artefakte unter ``out``, Checkpoints über ``reporter``.

    Artefakt-URLs zeigen auf das Cockpit (``/artefakt/<auftrag>/…``).
    """

    def __init__(self, out: Path, auftrag_id: str, reporter: Reporter) -> None:
        self.out = out
        self.auftrag_id = auftrag_id
        self.reporter = reporter
        self.maschine = socket.gethostname()
        self.werkzeuge = _werkzeuge()

    def url(self, name: str) -> str:
        return f"/artefakt/{self.auftrag_id}/{name}"

    def artefakt(self, name: str, art: ArtefaktArt = "datei") -> Artefakt:
        return Artefakt(art, name, self.url(name))

    def melde(self, schritt: str, status: Status, **felder: Any) -> Checkpoint:
        cp = Checkpoint(
            self.auftrag_id, schritt, status, AGENT, self.maschine, self.werkzeuge, **felder
        )
        self.reporter.checkpoint(cp)
        return cp

    def schreibe(self, name: str, data: Any) -> Path:
        p = self.out / name
        p.write_text(
            json.dumps(data, sort_keys=True, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        return p


def run_batch(
    inputs: list[Path], out: Path, auftrag_id: str, reporter: Reporter, titel: str = "Pilot-Lauf"
) -> dict[str, Any]:
    """Upload bis Freigabe (blockiert); liefert das Batch-Manifest. Originale bleiben unberührt."""
    out.mkdir(parents=True, exist_ok=True)
    reporter.auftrag(auftrag_id, titel)
    lauf = Lauf(out, auftrag_id, reporter)
    t0 = time.perf_counter()

    # 1 Upload: Validierung nach Inhalt, Hash, Dedup.
    eingaben: list[dict[str, Any]] = []
    gesehen: set[str] = set()
    abgelehnt: list[str] = []
    for i, p in enumerate(inputs, 1):
        try:
            m = validate_media(p)
        except MediaRejectedError as err:
            abgelehnt.append(f"{p.name}: {err.reason}")
            continue
        if m.sha256 in gesehen:
            abgelehnt.append(f"{p.name}: Dublette")
            continue
        gesehen.add(m.sha256)
        eingaben.append(
            {
                "asset_id": f"asset-{i}",
                "datei": p.name,
                "pfad": str(p.resolve()),
                "kind": m.kind,
                "sha256": m.sha256,
                "size_bytes": m.size_bytes,
                "duration": m.duration,
                "width": m.width,
                "height": m.height,
            }
        )
    lauf.schreibe("eingaben.json", {"eingaben": eingaben, "abgelehnt": abgelehnt})
    videos = [e for e in eingaben if e["kind"] == "video"]
    if not videos:
        lauf.melde(
            "Upload",
            "fehlgeschlagen",
            eingabe=", ".join(p.name for p in inputs),
            fehler="kein gültiges Video: " + ("; ".join(abgelehnt) or "nur Bilder"),
            artefakte=[lauf.artefakt("eingaben.json")],
        )
        raise SystemExit(2)
    lauf.melde(
        "Upload",
        "fertig",
        eingabe=", ".join(p.name for p in inputs),
        ergebnis=f"{len(videos)} Video(s), {len(eingaben) - len(videos)} Bild(er) geprüft, "
        f"{len(abgelehnt)} abgelehnt; {time.perf_counter() - t0:.1f} s",
        artefakte=[lauf.artefakt("eingaben.json")],
    )

    # 2 Highlights: Szenen → Signale → Auswahl, je Asset ein Analyse-JSON.
    t1 = time.perf_counter()
    analysen: list[AnalysisResult] = []
    for ein in eingaben:
        a = analyze_asset(Path(ein["pfad"]), ein["asset_id"])
        (out / f"analyse-{ein['asset_id']}.json").write_text(a.to_json(), encoding="utf-8")
        analysen.append(a)
    kandidaten = sorted(
        (h for a in analysen for h in a.highlights),
        key=lambda h: (-h.confidence, h.asset_id, h.start),
    )
    highlights = lauf.schreibe("highlights.json", {"highlights": [asdict(h) for h in kandidaten]})
    artefakte = [lauf.artefakt(highlights.name)] + [
        lauf.artefakt(f"analyse-{a.asset_id}.json") for a in analysen
    ]
    if len(kandidaten) < VARIANTEN:
        lauf.melde(
            "Highlights",
            "fehlgeschlagen",
            eingabe=f"{len(analysen)} Assets",
            fehler=f"nur {len(kandidaten)} Highlight(s) ab {MIN_LEN:.0f} s, {VARIANTEN} gebraucht",
            artefakte=artefakte,
        )
        raise SystemExit(2)
    lauf.melde(
        "Highlights",
        "fertig",
        eingabe=f"{len(analysen)} Assets",
        ergebnis=f"{len(kandidaten)} Highlights (Heuristik: Bewegung je Szene, keine Aussage über "
        f"Reichweite); bestes {kandidaten[0].asset_id} {kandidaten[0].start:.1f}–"
        f"{kandidaten[0].end:.1f} s; {time.perf_counter() - t1:.1f} s",
        artefakte=artefakte,
    )

    # 3 Videoschnitt: die besten Highlights aus möglichst verschiedenen Assets als 9:16 mit Cover.
    t2 = time.perf_counter()
    varianten: list[Variante] = []
    quelle = {e["asset_id"]: e for e in eingaben}
    for n, h in enumerate(waehle_varianten(kandidaten, VARIANTEN), 1):
        name = f"variante-{n}"
        try:
            r = render_vertical(
                Path(quelle[h.asset_id]["pfad"]), h.start, h.end, out / f"{name}.mp4"
            )
            extract_cover(r.path, at=min(1.0, r.duration / 2), out=out / f"{name}.jpg")
        except Exception as err:
            lauf.melde(
                "Videoschnitt",
                "fehlgeschlagen",
                eingabe=f"{h.asset_id} {h.start:.1f}–{h.end:.1f} s",
                fehler=f"{name}: {err}"[:4000],
                artefakte=[lauf.artefakt(f"{v.video}", "vorschau") for v in varianten],
            )
            raise SystemExit(1) from err
        varianten.append(
            Variante(
                name,
                h.asset_id,
                quelle[h.asset_id]["datei"],
                h.start,
                h.end,
                h.confidence,
                f"{name}.mp4",
                f"{name}.jpg",
            )
        )
    lauf.schreibe(
        "varianten.json",
        {
            "varianten": [asdict(v) for v in varianten],
            "untertitel": "nicht erzeugt (Spracherkennung SIN-1357 offen)",
        },
    )
    vorschau = [
        a
        for v in varianten
        for a in (lauf.artefakt(v.video, "vorschau"), lauf.artefakt(v.cover, "vorschau"))
    ] + [lauf.artefakt("varianten.json")]
    lauf.melde(
        "Videoschnitt",
        "fertig",
        eingabe="; ".join(f"{v.quelle} {v.start:.1f}–{v.end:.1f} s" for v in varianten),
        ergebnis=f"{len(varianten)} Varianten 1080x1920 H.264 + Cover; ohne Untertitel; "
        f"{time.perf_counter() - t2:.1f} s",
        artefakte=vorschau,
    )

    # 4 Qualitätsprüfung: ffprobe-Abnahme jeder Datei.
    pruefungen = [pruefe_variante(out, v) for v in varianten]
    lauf.schreibe("pruefung.json", {"pruefungen": [asdict(p) for p in pruefungen]})
    befund = "; ".join(f"{p.name}: {p.befund}" for p in pruefungen)
    if not all(p.ok for p in pruefungen):
        lauf.melde(
            "Qualitätsprüfung",
            "fehlgeschlagen",
            eingabe=", ".join(v.video for v in varianten),
            fehler=befund,
            artefakte=[lauf.artefakt("pruefung.json", "test")],
        )
        raise SystemExit(1)
    lauf.melde(
        "Qualitätsprüfung",
        "fertig",
        eingabe=", ".join(v.video for v in varianten),
        ergebnis=befund,
        artefakte=[lauf.artefakt("pruefung.json", "test")],
    )

    # 5 Freigabe: wartet auf Sinan im Cockpit.
    lauf.melde(
        "Freigabe",
        "blockiert",
        eingabe=", ".join(v.video for v in varianten),
        entscheidung=f"{len(varianten)} Varianten ansehen (Vorschau unter Videoschnitt) und "
        "freigeben oder ablehnen; erst dann läuft der Export.",
        artefakte=vorschau,
    )
    manifest = {
        "auftrag": auftrag_id,
        "pipeline_version": PIPELINE_VERSION,
        "eingaben": eingaben,
        "varianten": [asdict(v) for v in varianten],
        "pruefungen": [asdict(p) for p in pruefungen],
        "dauer_s": round(time.perf_counter() - t0, 1),
    }
    lauf.schreibe("batch.json", manifest)
    return manifest


def export_batch(out: Path, auftrag_id: str, reporter: Reporter) -> Path | None:
    """Nach Freigabe: Varianten samt Cover und Manifest nach ``out/export``; sonst nichts."""
    lauf = Lauf(out, auftrag_id, reporter)
    antwort = reporter.freigabe(auftrag_id)
    if antwort is None:
        return None
    if antwort == "abgelehnt":
        lauf.melde("Export", "fehlgeschlagen", fehler="Freigabe abgelehnt; nichts exportiert")
        return None
    manifest = json.loads((out / "batch.json").read_text(encoding="utf-8"))
    ziel = out / "export"
    ziel.mkdir(exist_ok=True)
    dateien: list[str] = []
    for v in manifest["varianten"]:
        for name in (v["video"], v["cover"]):
            shutil.copyfile(out / name, ziel / name)
            dateien.append(name)
    (ziel / "export.json").write_text(
        json.dumps(
            {
                "auftrag": auftrag_id,
                "freigabe": antwort,
                "dateien": dateien,
                "quellen": [e["sha256"] for e in manifest["eingaben"]],
            },
            sort_keys=True,
            indent=1,
        ),
        encoding="utf-8",
    )
    lauf.melde(
        "Export",
        "fertig",
        eingabe="Freigabe: " + antwort,
        ergebnis=f"{len(dateien)} Dateien nach export/",
        artefakte=[
            lauf.artefakt(f"export/{n}", "vorschau" if n.endswith(".mp4") else "datei")
            for n in dateien
        ]
        + [lauf.artefakt("export/export.json")],
    )
    return ziel


def beispiel(ziel: Path) -> list[Path]:
    """Synthetisches Material (kein Creator-Video): zwei Clips mit Schnitten und Ton, ein Bild."""
    ziel.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg fehlt")
    base = [ffmpeg, "-v", "error", "-nostdin", "-y"]
    clips = {
        "clip-a.mp4": [
            "testsrc2=duration=4:size=1280x720:rate=25",
            "color=c=blue:duration=3:size=1280x720:rate=25",
            "testsrc=duration=4:size=1280x720:rate=25",
        ],
        "clip-b.mp4": [
            "mandelbrot=size=1280x720:rate=25",
            "color=c=green:duration=3:size=1280x720:rate=25",
        ],
    }
    out: list[Path] = []
    for name, quellen in clips.items():
        p = ziel / name
        args = list(base)
        for q in quellen:
            args += ["-f", "lavfi", "-t", "4", "-i", q]
        args += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={4 * len(quellen)}"]
        args += [
            "-filter_complex",
            "".join(f"[{i}:v]" for i in range(len(quellen)))
            + f"concat=n={len(quellen)}:v=1:a=0,format=yuv420p[v]",
            "-map",
            "[v]",
            "-map",
            f"{len(quellen)}:a",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            "-shortest",
            str(p),
        ]
        subprocess.run(args, check=True)
        out.append(p)
    bild = ziel / "foto.png"
    subprocess.run(
        [*base, "-f", "lavfi", "-i", "testsrc2=size=1080x1350:rate=1", "-frames:v", "1", str(bild)],
        check=True,
    )
    out.append(bild)
    return out
