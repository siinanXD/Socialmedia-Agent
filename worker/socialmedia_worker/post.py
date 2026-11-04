"""Aus mehreren Clips und Fotos wird ein Post (SIN-1360, SIN-1361): Storyboard, Render mit FFmpeg.

Deterministisch und ohne Modell. Musik fehlt bewusst (Sinan 02.11.: der Trend-Sound kommt beim
Posten in der App dazu). Tempo und Längen sind feste Werte, keine Trend-Messung (SIN-1374).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from socialmedia_worker.highlights import Highlight
from socialmedia_worker.render import _VERTICAL_FILTER, RENDER_TIMEOUT_S, RenderError, _run_ffmpeg
from socialmedia_worker.scenes import FfmpegNotFoundError
from socialmedia_worker.signals import _has_audio

# shortcut: feste Längen statt gemessenem Reel-Tempo, ersetzen mit der Referenz-Analyse (SIN-1374).
CLIP_S = 3.5
FOTO_S = 2.0
UEBERGANG_S = 0.25
ZIEL_MAX_S = 30.0
FPS = 30
ZOOM = 0.06
LAUTHEIT_ZIEL = -14.0
_AUDIO = "aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:{d},asetpts=PTS-STARTPTS"


@dataclass(frozen=True)
class Baustein:
    art: Literal["video", "foto"]
    quelle: str
    start: float
    dauer: float
    confidence: float | None


@dataclass(frozen=True)
class Storyboard:
    strategie: Literal["hook", "chronologisch"]
    bausteine: list[Baustein]

    @property
    def dauer(self) -> float:
        d = sum(b.dauer for b in self.bausteine)
        return d - max(0, len(self.bausteine) - 1) * UEBERGANG_S

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategie": self.strategie,
            "dauer": round(self.dauer, 3),
            "bausteine": [asdict(b) for b in self.bausteine],
        }


def waehle_varianten(kandidaten: list[Highlight], anzahl: int) -> list[Highlight]:
    """Erst das Beste je Asset, dann der Rest: Fenster derselben Aufnahme ähneln sich."""
    gesehen: set[str] = set()
    erste: list[Highlight] = []
    rest: list[Highlight] = []
    for h in kandidaten:
        (rest if h.asset_id in gesehen else erste).append(h)
        gesehen.add(h.asset_id)
    return (erste + rest)[:anzahl]


def _folge(clips: list[Highlight], quellen: Mapping[str, str], fotos: list[str]) -> list[Baustein]:
    """Zwei Clips zum Einstieg, danach abwechselnd Foto und Clip, bis das Ziel erreicht ist."""
    videos = [
        Baustein("video", quellen[h.asset_id], h.start, min(CLIP_S, h.end - h.start), h.confidence)
        for h in clips
    ]
    bilder = [Baustein("foto", f, 0.0, FOTO_S, None) for f in fotos]
    alle = videos[:2]
    rest_v, rest_b = videos[2:], bilder
    while rest_v or rest_b:
        if rest_b:
            alle.append(rest_b[0])
            rest_b = rest_b[1:]
        if rest_v:
            alle.append(rest_v[0])
            rest_v = rest_v[1:]
    folge: list[Baustein] = []
    summe = 0.0
    for b in alle:
        neu = summe + b.dauer - (UEBERGANG_S if folge else 0.0)
        if neu > ZIEL_MAX_S:
            break
        folge.append(b)
        summe = neu
    return folge


def baue_storyboards(
    kandidaten: list[Highlight], quellen: Mapping[str, str], fotos: list[str]
) -> list[Storyboard]:
    """Hook zuerst und chronologisch; ergeben beide dieselbe Folge, bleibt eine Variante."""
    if not kandidaten:
        return []
    beste = sorted(kandidaten, key=lambda h: (-h.confidence, h.asset_id, h.start))
    reihenfolge = {asset: i for i, asset in enumerate(quellen)}
    zeitlich = sorted(kandidaten, key=lambda h: (reihenfolge[h.asset_id], h.start))
    hook = Storyboard("hook", _folge(waehle_varianten(beste, len(beste)), quellen, fotos))
    chrono = Storyboard("chronologisch", _folge(zeitlich, quellen, fotos))
    return [hook] if hook.bausteine == chrono.bausteine else [hook, chrono]


def _eingaben(b: Baustein, pfad: Path) -> list[str]:
    if b.art == "foto":
        return ["-loop", "1", "-framerate", str(FPS), "-t", str(b.dauer), "-i", str(pfad)]
    return ["-ss", str(b.start), "-t", str(b.dauer), "-i", str(pfad)]


def _bild_filter(b: Baustein) -> str:
    if b.art == "video":
        return f"{_VERTICAL_FILTER},fps={FPS},format=yuv420p"
    n = round(b.dauer * FPS)
    return (
        # Doppelte Größe vor dem Zoom, sonst ruckelt zoompan an ganzen Pixeln.
        "scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
        f"zoompan=z='1+{ZOOM}*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:"
        f"s=1080x1920:fps={FPS},setsar=1,format=yuv420p"
    )


def render_post(board: Storyboard, quellen: Mapping[str, Path], out: Path) -> Path:
    """Ein 1080x1920-MP4 aus allen Bausteinen, mit Überblendung und einheitlicher Lautstärke."""
    args: list[str] = []
    filter_teile: list[str] = []
    audio_quelle: list[int] = []
    teile = board.bausteine
    for i, b in enumerate(teile):
        pfad = quellen[b.quelle]
        args += _eingaben(b, pfad)
        filter_teile.append(f"[{i}:v]{_bild_filter(b)},trim=0:{b.dauer},setpts=PTS-STARTPTS[v{i}]")
    for i, b in enumerate(teile):
        pfad = quellen[b.quelle]
        if b.art == "video" and _has_audio(pfad):
            audio_quelle.append(i)
        else:  # Stille, damit jede Überblendung eine Tonspur hat
            args += ["-f", "lavfi", "-t", str(b.dauer), "-i", "anullsrc=r=48000:cl=stereo"]
            audio_quelle.append(len(teile) + sum(1 for x in audio_quelle if x >= len(teile)))
        filter_teile.append(f"[{audio_quelle[i]}:a]{_AUDIO.format(d=b.dauer)}[a{i}]")
    v, a = "v0", "a0"
    versatz = 0.0
    for i in range(1, len(teile)):
        versatz += teile[i - 1].dauer - UEBERGANG_S
        filter_teile.append(
            f"[{v}][v{i}]xfade=transition=fade:duration={UEBERGANG_S}:offset={versatz:.3f}[vx{i}]"
        )
        filter_teile.append(f"[{a}][a{i}]acrossfade=d={UEBERGANG_S}[ax{i}]")
        v, a = f"vx{i}", f"ax{i}"
    roh = out.with_name(f".{out.stem}.roh{out.suffix}")
    if out.exists():
        raise FileExistsError(f"{out} exists; refusing to overwrite")
    roh.unlink(missing_ok=True)
    _run_ffmpeg(
        [
            *args,
            "-filter_complex",
            ";".join(filter_teile),
            "-map",
            f"[{v}]",
            "-map",
            f"[{a}]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
        ],
        roh,
        RENDER_TIMEOUT_S,
    )
    try:
        # Erst messen, dann anpassen: einstufiges loudnorm lag bei echtem Material 2,2 LU daneben.
        gemessen = lautheit(roh)
        if gemessen is None:
            raise RenderError("Post hat keine messbare Tonspur")
        _run_ffmpeg(
            ["-i", str(roh), "-c:v", "copy",
             "-af", f"volume={LAUTHEIT_ZIEL - gemessen:.2f}dB,alimiter=limit=0.84:level=disabled",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"],
            out,
            RENDER_TIMEOUT_S,
        )  # fmt: skip
    finally:
        roh.unlink(missing_ok=True)
    return out


def lautheit(path: Path) -> float | None:
    """Gemessene Lautheit in LUFS (ebur128); None, wenn es keine Tonspur gibt."""
    if not _has_audio(path):
        return None
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise FfmpegNotFoundError("ffmpeg not found on PATH; install FFmpeg (ffmpeg.org)")
    proc = subprocess.run(
        [ffmpeg, "-hide_banner", "-nostats", "-nostdin", "-i", str(path), "-map", "0:a:0",
         "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
        capture_output=True, text=True, timeout=RENDER_TIMEOUT_S,
        encoding="utf-8", errors="replace",
    )  # fmt: skip
    text = re.sub(r"\s+", " ", proc.stderr)
    m = re.search(r"Integrated loudness: I: (-?\d+(?:\.\d+)?) LUFS", text)
    return float(m.group(1)) if m else None
