import json
import subprocess
from pathlib import Path

import pytest

from socialmedia_worker.carousel import (
    HEIGHT,
    MANIFEST_NAME,
    MAX_SLIDES,
    WIDTH,
    CarouselError,
    build_carousel,
    validate_carousel,
)
from socialmedia_worker.validate import MediaRejectedError, validate_media

SCHEMA = Path(__file__).parent.parent / "schemas" / "carousel.v1.json"


def _image(path: Path, source: str) -> Path:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-nostdin", "-y", "-f", "lavfi", "-i", source,
         "-frames:v", "1", str(path)],
        check=True,
    )
    return path


def _wave(path: Path, a: int, b: int) -> Path:
    """Streifenmuster; (a, b) bestimmt Richtung und Dichte, damit die Bilder verschieden sind."""
    lum = f"128+110*sin(PI*({a}*X/W+{b}*Y/H))"
    return _image(path, f"color=size=320x400,format=gray,geq=lum='{lum}'")


@pytest.fixture
def four(tmp_path: Path) -> dict[str, Path]:
    """Vier Bilder mit verschiedenen Seitenverhältnissen (quer, hoch, quadratisch, 4:3)."""
    return {
        "quer": _image(tmp_path / "quer.png", "testsrc2=size=1280x720"),
        "hoch": _image(tmp_path / "hoch.jpg", "smptebars=size=720x1280"),
        "quadrat": _image(tmp_path / "quadrat.png", "rgbtestsrc=size=600x600"),
        "vierdrei": _image(tmp_path / "vierdrei.jpg", "testsrc=size=800x600"),
    }


def test_four_images_give_four_slides_of_exact_size(four: dict[str, Path], tmp_path: Path) -> None:
    before = {k: p.read_bytes() for k, p in four.items()}
    result = build_carousel(four, out_dir=tmp_path / "out")

    assert len(result.slides) == 4
    for path in result.slides:
        media = validate_media(path)  # lesbares Bild
        assert (media.kind, media.codec, media.width, media.height) == (
            "image", "mjpeg", WIDTH, HEIGHT,
        )
    assert (WIDTH, HEIGHT) == (1080, 1350)
    assert result.cover == result.slides[0]
    assert {k: p.read_bytes() for k, p in four.items()} == before  # Originale unverändert

    data = json.loads(result.manifest.read_text(encoding="utf-8"))
    assert result.manifest.name == MANIFEST_NAME == "carousel-manifest.v1.json"
    validate_carousel(data)
    assert data["approval_state"] == "wartet_auf_freigabe"
    assert data["cover"] == "slide-01.jpg"
    assert sorted(s["asset_id"] for s in data["slides"]) == sorted(four)
    assert [s["position"] for s in data["slides"]] == [1, 2, 3, 4]
    for s in data["slides"]:
        assert s["sha256"] == validate_media(four[s["asset_id"]]).sha256
        assert s["rationale"]
    assert data["omitted"] == []


def test_schema_file_matches_the_manifest(four: dict[str, Path], tmp_path: Path) -> None:
    data = json.loads(build_carousel(four, out_dir=tmp_path / "out").manifest.read_text("utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert set(schema["required"]) == set(data)
    assert schema["properties"]["version"]["const"] == data["version"]
    assert schema["properties"]["slides"]["maxItems"] == MAX_SLIDES
    assert set(schema["properties"]["slides"]["items"]["required"]) == set(data["slides"][0])
    with pytest.raises(ValueError, match="approval_state"):
        validate_carousel({**data, "approval_state": "freigegeben"})


def test_same_input_gives_the_same_manifest(four: dict[str, Path], tmp_path: Path) -> None:
    a = build_carousel(four, out_dir=tmp_path / "a").manifest.read_bytes()
    b = build_carousel(dict(reversed(four.items())), out_dir=tmp_path / "b").manifest.read_bytes()
    assert a == b


def test_manual_order_and_captions(four: dict[str, Path], tmp_path: Path) -> None:
    order = ["vierdrei", "quer", "hoch"]
    result = build_carousel(four, order, {"quer": "Erster Tag"}, out_dir=tmp_path / "out")
    data = json.loads(result.manifest.read_text(encoding="utf-8"))
    assert [s["asset_id"] for s in data["slides"]] == order
    assert [s["caption"] for s in data["slides"]] == [None, "Erster Tag", None]
    assert data["omitted"] == [
        {"asset_id": "quadrat", "sha256": validate_media(four["quadrat"]).sha256,
         "reason": "nicht_in_reihenfolge"}
    ]
    with pytest.raises(ValueError, match="unbekannt"):
        build_carousel(four, ["quer", "fehlt"], out_dir=tmp_path / "x")


def test_better_picture_comes_first(four: dict[str, Path], tmp_path: Path) -> None:
    blurred = tmp_path / "weich.png"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(four["vierdrei"]), "-vf", "gblur=sigma=12",
         str(blurred)],
        check=True,
    )
    result = build_carousel({"a-weich": blurred, "z-scharf": four["quer"]}, out_dir=tmp_path / "o")
    data = json.loads(result.manifest.read_text(encoding="utf-8"))
    assert [s["asset_id"] for s in data["slides"]] == ["z-scharf", "a-weich"]
    assert "unscharf" in data["slides"][1]["rationale"]


def test_near_duplicate_is_left_out_with_reason(four: dict[str, Path], tmp_path: Path) -> None:
    twin = tmp_path / "zwilling.png"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(four["quer"]), "-vf", "eq=brightness=0.05",
         str(twin)],
        check=True,
    )
    result = build_carousel({**four, "zwilling": twin}, out_dir=tmp_path / "out")
    data = json.loads(result.manifest.read_text(encoding="utf-8"))
    assert len(data["slides"]) == 4
    (weg,) = data["omitted"]
    kept = ({"quer", "zwilling"} - {weg["asset_id"]}).pop()
    assert weg["reason"] == f"near_duplicate_of:{kept}"


def test_more_than_ten_images_keeps_the_best_ten(tmp_path: Path) -> None:
    images = {
        f"bild-{a}{b}": _wave(tmp_path / f"w{a}{b}.png", a, b)
        for a in (1, 2, 3, 4)
        for b in (0, 1, 2)
    }
    assert len(images) == 12
    result = build_carousel(images, out_dir=tmp_path / "out", max_distance=0)
    data = json.loads(result.manifest.read_text(encoding="utf-8"))
    assert len(result.slides) == len(data["slides"]) == MAX_SLIDES == 10
    assert [o["reason"] for o in data["omitted"]] == ["ueber_limit:10"] * 2
    ids = [s["asset_id"] for s in data["slides"]] + [o["asset_id"] for o in data["omitted"]]
    assert sorted(ids) == sorted(images)  # nichts verschwindet still
    validate_carousel(data)


def test_one_image_is_an_honest_error_and_writes_nothing(
    four: dict[str, Path], tmp_path: Path
) -> None:
    out = tmp_path / "out"
    with pytest.raises(CarouselError, match="mindestens 2"):
        build_carousel({"quer": four["quer"]}, out_dir=out)
    assert not out.exists()


def test_rejects_videos_and_refuses_to_overwrite(four: dict[str, Path], tmp_path: Path) -> None:
    clip = tmp_path / "clip.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240",
         str(clip)],
        check=True,
    )
    with pytest.raises(MediaRejectedError, match="not an image"):
        build_carousel({**four, "clip": clip}, out_dir=tmp_path / "v")
    build_carousel(four, out_dir=tmp_path / "out")
    with pytest.raises(FileExistsError):
        build_carousel(four, out_dir=tmp_path / "out")
