# Socialmedia-Agent

Autonomous, multi-creator social-media production platform — **planning stage; not yet implemented**.

Pilot: PXUL WRLD (fitness). Own product repository, separate from Leitstand.

## Mission
Upload multiple raw videos and photos or import a watched folder; identify promising highlights with provenance and timestamps; assemble 9:16 Reels/Shorts and carousels with captions/covers; optionally analyze lawful competitor/trend references; propose licensed audio; approve, publish through authorized APIs and learn from real insights.

## Current status
- No working application, deployment or automated publishing exists yet.
- [Linear SIN-1077](https://linear.app/sinan-kahraman/issue/SIN-1077) tracks the project.
- Leitstand is the future orchestrator, not a runtime dependency for the first MVP.
- Build released by Sinan on 27.10.2026: agents build autonomously from Linear (see `AGENTS.md` for stack and rules). Still no paid services, production deployment or publishing without explicit authorization.

See `docs/` and `AGENTS.md` in the planning pull request for architecture, phased roadmap, contracts, acceptance criteria and implementation guidance.

## Worker lokal
Voraussetzungen: [uv](https://docs.astral.sh/uv/) und FFmpeg (`ffmpeg`/`ffprobe` im PATH).

```
cd worker && uv sync && uv run pytest
uv run ruff check . && uv run mypy .
```

Stand: `worker/` enthaelt nur `probe(path)` (Dauer, Breite, Hoehe per ffprobe). Keine Queue, kein Upload.

Render-Baustein (`socialmedia_worker.render`, FFmpeg per Subprozess ohne Shell):

```python
from pathlib import Path
from socialmedia_worker.render import extract_cover, render_vertical

result = render_vertical(Path("quelle.mp4"), start=1.0, end=3.0, out=Path("clip.mp4"))
# 1080x1920, H.264/AAC, Mitte zugeschnitten; Quelle bleibt unveraendert
extract_cover(result.path, at=1.0, out=Path("cover.jpg"))  # ein JPEG-Frame
```

`ValueError` bei ungueltigem Zeitbereich (`0 <= start < end <= Dauer`) oder `out == src`; `FfmpegNotFoundError`
ohne ffmpeg; `RenderError` bei ffmpeg-Exit != 0 (unvollstaendige Ausgabe wird geloescht). Quellen ohne Audio
werden ohne Tonspur gerendert. Kein Subjekt-Tracking, keine Untertitel, keine Musik, keine Varianten.
