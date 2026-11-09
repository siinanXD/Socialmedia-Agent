import subprocess
from dataclasses import dataclass
from pathlib import Path

from socialmedia_worker.highlights import Highlight
from socialmedia_worker.signals import ffmpeg_path
from socialmedia_worker.validate import validate_media

HASH_TIMEOUT_S = 60
_W, _H = 9, 8  # dHash: 8 left/right comparisons per row, 8 rows = 64 bits
# Hamming distance (of 64 bits) up to which two frames count as "almost the same picture".
# Measured on generated clips (tests/test_dedupe.py): same source with noise and a brightness
# shift 0 bits, different test patterns 16-41. 10 is the customary dHash threshold in between;
# it is not calibrated on real footage.
MAX_DISTANCE = 10


@dataclass(frozen=True)
class Dropped:
    highlight: Highlight
    reason: str


def frame_hash(path: Path, at: float = 0.0) -> int:
    """64-bit difference hash of the frame at `at` seconds (photos: at=0).

    The frame is scaled to 9x8 grey pixels; each bit says whether a pixel is brighter than its
    right neighbour. Visual similarity only: it knows nothing about what the picture shows.
    """
    ffmpeg = ffmpeg_path()
    media = validate_media(path)
    if media.kind == "video":
        if media.duration is None or not 0 <= at < media.duration:
            raise ValueError(f"invalid at: need 0 <= at < {media.duration}s, got {at}")
    elif at != 0:
        raise ValueError(f"invalid at: {path.name} is an image, got {at}")
    seek = ["-ss", str(at)] if media.kind == "video" else []  # -ss on a JPEG yields no frame
    proc = subprocess.run(
        [ffmpeg, "-v", "error", "-nostdin", *seek, "-i", str(path), "-frames:v", "1",
         "-vf", f"scale={_W}:{_H}:flags=area,format=gray", "-f", "rawvideo", "-"],
        capture_output=True,
        timeout=HASH_TIMEOUT_S,
    )
    px = proc.stdout
    if proc.returncode != 0 or len(px) != _W * _H:
        raise ValueError(f"{path.name}: ffmpeg produced no frame at {at}s")
    value = 0
    for row in range(_H):
        for col in range(_W - 1):
            value = value << 1 | (px[row * _W + col] > px[row * _W + col + 1])
    return value


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def highlight_id(h: Highlight) -> str:
    return f"{h.asset_id}@{h.start:.3f}"


def drop_near_duplicates(
    highlights: list[Highlight], hashes: list[int], max_distance: int = MAX_DISTANCE
) -> tuple[list[Highlight], list[Dropped]]:
    """Split highlights into (kept, dropped); `hashes[i]` is the frame_hash of `highlights[i]`.

    Of two near duplicates (also from different files) the higher confidence wins, then the
    earlier one (start, asset_id). Kept stay in input order; each dropped one names its winner
    as reason "near_duplicate_of:<asset_id>@<start>", so nothing disappears silently.
    """
    if len(highlights) != len(hashes):
        raise ValueError("highlights and hashes must have the same length")
    ranked = sorted(
        range(len(highlights)),
        key=lambda i: (-highlights[i].confidence, highlights[i].start, highlights[i].asset_id, i),
    )
    winners: list[int] = []
    reason: dict[int, str] = {}
    for i in ranked:
        twin = next((w for w in winners if hamming(hashes[i], hashes[w]) <= max_distance), None)
        if twin is None:
            winners.append(i)
        else:
            reason[i] = f"near_duplicate_of:{highlight_id(highlights[twin])}"
    kept = [h for i, h in enumerate(highlights) if i not in reason]
    return kept, [Dropped(highlights[i], reason[i]) for i in sorted(reason)]
