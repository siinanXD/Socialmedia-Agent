from dataclasses import dataclass
from pathlib import Path

from socialmedia_worker.signals import ffmpeg_path, filter_values
from socialmedia_worker.validate import MediaRejectedError, validate_media

# Edge-map mean luma (0..255) after edgedetect on a 640 px wide copy; this much counts as sharp.
# Measured on generated test images: sharp 1.5-3.7, the same images blurred 0.0-0.2.
SHARPNESS_FULL_SCALE = 1.5
SHARPNESS_MIN = 0.35
UNDEREXPOSED_BELOW = 0.35  # mean luma / 255
OVEREXPOSED_ABOVE = 0.8


@dataclass(frozen=True)
class Quality:
    sharpness: float
    exposure: float
    reasons: list[str]


def _mean_luma(path: Path, vf: str) -> float:
    values = filter_values(
        ["-i", str(path), "-vf", f"{vf}signalstats,metadata=print:file=-", "-frames:v", "1"],
        "lavfi.signalstats.YAVG",
        path.name,
    )
    if not values:
        raise ValueError(f"{path.name}: ffmpeg produced no frame statistics")
    return values[0]


def image_quality(path: Path) -> Quality:
    """Sharpness and exposure (each 0..1) of a JPEG/PNG photo or a frame taken from a video.

    sharpness: mean luma of the `edgedetect` map of a 640 px wide copy, divided by 8 and capped
    at 1 (soft or blurred images have few edges; a sharp but plain surface also scores low).
    exposure: 1 - |mean luma - 128| / 128, so mid-grey is 1.0 and pure black or white 0.0.
    `reasons` names the problems found ("unscharf", "unterbelichtet", "überbelichtet"); empty
    when none. Heuristic, no model; it says nothing about aesthetics or reach. validate_media
    runs before ffmpeg.
    """
    ffmpeg_path()
    media = validate_media(path)
    if media.kind != "image":
        raise MediaRejectedError("unsupported_format", f"{path.name}: not an image")
    if media.width * media.height == 0:  # ffprobe accepts a few junk bytes as an empty PNG
        raise MediaRejectedError("truncated_or_corrupt", f"{path.name}: empty image")
    scale = "scale=640:-2:flags=bilinear,"
    luma = _mean_luma(path, scale)
    edges = _mean_luma(path, f"{scale}edgedetect=low=0.1:high=0.4,")
    sharpness = round(min(edges / SHARPNESS_FULL_SCALE, 1.0), 4)
    exposure = round(max(1.0 - abs(luma - 128.0) / 128.0, 0.0), 4)
    reasons: list[str] = []
    if sharpness < SHARPNESS_MIN:
        reasons.append("unscharf")
    if luma / 255.0 < UNDEREXPOSED_BELOW:
        reasons.append("unterbelichtet")
    elif luma / 255.0 > OVEREXPOSED_ABOVE:
        reasons.append("überbelichtet")
    return Quality(sharpness, exposure, reasons)
