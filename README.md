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

## App lokal
Voraussetzung: Node 22 (wie in `build.yml`); für die Anmeldung zusätzlich Docker und die Supabase CLI (siehe „Datenbank lokal“).

```
supabase start                      # lokale Supabase; `supabase status` zeigt API URL und anon key
cp .env.example .env.local          # NEXT_PUBLIC_SUPABASE_URL und NEXT_PUBLIC_SUPABASE_ANON_KEY eintragen
npm ci
npm run dev                         # http://localhost:3000 -> Weiterleitung auf /login
npm run typecheck && npm test && npm run build
```

Stand: Anmeldung mit Supabase Auth (SIN-1377): Registrierung (`/registrieren`), Login (`/login`), Abmelden, alle anderen Routen nur mit Session (`proxy.ts`; `/api/health` bleibt offen). Beim ersten Aufruf von `/` nach der Anmeldung legt `ensureCreator()` die Zeile in `social_media.creators` an (idempotent, unter RLS). In der App steckt nur der öffentliche anon-Schlüssel, kein Service-Role-Schlüssel. Sonst weiter nur Gerüst: kein Upload, keine Medienfunktion, kein Deployment. Das lokale Supabase hat E-Mail-Bestätigung aus (`supabase/config.toml`); ist sie am Zielprojekt an, verweist die Registrierung auf `/login` mit Hinweis.

## Worker lokal
Voraussetzungen: [uv](https://docs.astral.sh/uv/) und FFmpeg (`ffmpeg`/`ffprobe` im PATH).

```
cd worker && uv sync && uv run pytest
uv run ruff check . && uv run mypy .
```

Stand: `worker/` enthaelt `probe(path)` (Dauer, Breite, Hoehe per ffprobe), die Medien-Validierung (SIN-1173), die Szenenerkennung (SIN-1165) und den Render-Baustein (SIN-1166). Keine Queue, kein Upload.

## Datenbank lokal
Voraussetzungen: Docker und die [Supabase CLI](https://supabase.com/docs/guides/local-development).

```
supabase db start   # wendet supabase/migrations auf eine lokale Datenbank an
supabase test db    # pgTAP-Tests aus supabase/tests
```

Stand: Schema `social_media` mit `creators`, `assets`, `jobs` und RLS über `creator_id` (SIN-1168). Kein Storage-Bucket, keine Anbindung der App. Läuft lokal schon ein anderes Supabase-Projekt auf Port 54322, dort `supabase stop` oder den Port in `supabase/config.toml` für den Lauf ändern.

Szenenerkennung:

```python
from pathlib import Path
from socialmedia_worker.probe import probe
from socialmedia_worker.scenes import detect_scenes, to_segments

path = Path("clip.mp4")
cuts = detect_scenes(path, threshold=0.3)       # [SceneCut(time=1.0, score=0.69)]
segments = to_segments(cuts, probe(path).duration)  # [(0.0, 1.0), (1.0, 2.0)]
```

`detect_scenes` ruft `ffmpeg` (scene-Filter) als Subprozess auf. Bewiesen ist es nur an einem zur Laufzeit erzeugten Testclip mit einem harten Schnitt (`worker/tests/test_scenes.py`); wie gut die Erkennung auf echtem Material und mit dem Schwellwert 0,3 arbeitet, ist nicht gemessen. Keine Highlight-Bewertung.

Render-Baustein (`socialmedia_worker.render`, FFmpeg per Subprozess ohne Shell):

```python
from pathlib import Path
from socialmedia_worker.render import extract_cover, render_vertical

result = render_vertical(Path("quelle.mp4"), start=1.0, end=3.0, out=Path("clip.mp4"))
# 1080x1920, H.264/AAC, Mitte zugeschnitten; Quelle bleibt unveraendert
extract_cover(result.path, at=1.0, out=Path("cover.jpg"))  # ein JPEG-Frame, geprueft mit validate_media (Bild, ohne Dauer)
```

`ValueError` bei ungueltigem Zeitbereich (`0 <= start < end <= Dauer`, Cover `0 <= at < Dauer`) oder `out == src`;
`FileExistsError`, wenn `out` schon existiert (nichts wird ueberschrieben); `FfmpegNotFoundError` ohne ffmpeg;
`RenderError` bei ffmpeg-Exit != 0, leerer Ausgabe oder Timeout (600 s Render, 60 s Cover; unvollstaendige Ausgabe wird
geloescht). Vor dem Rendern prueft `validate_media` die Quelle (Container, Groesse, Dauer, Aufloesung; sonst `MediaRejectedError`); geschrieben wird in eine Temp-Datei, die erst nach der Pruefung als `out` erscheint. Quellen ohne Audio werden ohne Tonspur gerendert. Kein Subjekt-Tracking, keine Untertitel, keine Musik, keine Varianten.

Medien-Validierung: `validate_media(path, limits)` (`validate.py`) prueft eine Quelldatei vor jeder Verarbeitung nach Inhalt (ffprobe, nicht Dateiendung): Format-Allowlist (MP4/MOV, JPEG/PNG), Groesse (`MAX_UPLOAD_MB`, Standard 500), Dauer (Standard 30 min), Aufloesung (Standard 8K), liefert `kind`, Container, Codec, Masse, Dauer und SHA-256. Verstoss -> `MediaRejectedError` mit `reason`-Code. Die Datei wird nur gelesen. Teilstand: nur Worker-seitige Pruefung, kein Upload, kein Virenscan, keine Quota; eine abgeschnittene Datei mit Index am Dateianfang wird nicht erkannt.
