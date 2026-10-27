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

Stand: `worker/` enthaelt `probe(path)` (Dauer, Breite, Hoehe per ffprobe) und die Szenenerkennung (SIN-1165):

```python
from pathlib import Path
from socialmedia_worker.probe import probe
from socialmedia_worker.scenes import detect_scenes, to_segments

path = Path("clip.mp4")
cuts = detect_scenes(path, threshold=0.3)       # [SceneCut(time=1.0, score=0.69)]
segments = to_segments(cuts, probe(path).duration)  # [(0.0, 1.0), (1.0, 2.0)]
```

`detect_scenes` ruft `ffmpeg` (scene-Filter) als Subprozess auf. Bewiesen ist es nur an einem zur Laufzeit erzeugten Testclip mit einem harten Schnitt (`worker/tests/test_scenes.py`); wie gut die Erkennung auf echtem Material und mit dem Schwellwert 0,3 arbeitet, ist nicht gemessen. Keine Highlight-Bewertung, keine Queue, kein Upload, kein Rendering.
