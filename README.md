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

Stand: `worker/` enthaelt nur `probe(path)` (Dauer, Breite, Hoehe per ffprobe). Keine Queue, kein Upload, kein Rendering.

Medien-Validierung: `validate_media(path, limits)` (`validate.py`) prueft eine Quelldatei vor jeder Verarbeitung nach Inhalt (ffprobe, nicht Dateiendung): Format-Allowlist (MP4/MOV, JPEG/PNG), Groesse (`MAX_UPLOAD_MB`, Standard 500), Dauer (Standard 30 min), Aufloesung (Standard 8K), liefert `kind`, Container, Codec, Masse, Dauer und SHA-256. Verstoss -> `MediaRejectedError` mit `reason`-Code. Die Datei wird nur gelesen. Teilstand: nur Worker-seitige Pruefung, kein Upload, kein Virenscan, keine Quota; eine abgeschnittene Datei mit Index am Dateianfang wird nicht erkannt.
