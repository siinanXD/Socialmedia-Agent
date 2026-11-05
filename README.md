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

## Live testen
Jeder PR bekommt von Vercel eine Preview-URL (Kommentar des Vercel-Bots im PR); `main` geht nach Merge in Produktion (Vercel-Projekt `socialmedia-agent`, Hobby). Beide sind für das gemeinsame Supabase-Projekt vorgesehen, Daten liegen im Schema `social_media` (RLS).
- Produktion: Adresse noch nicht belegt (offen, SIN-1512). `https://socialmedia-agent.vercel.app` gehört nicht zu dieser App: ein Abruf am 03.11.2026 lieferte eine fremde Marketing-Seite („Nova — AI Social Media Agent“). Die echte Produktions-Adresse muss Sinan im Vercel-Projekt `socialmedia-agent` (Team siinanxds-projects) ablesen und hier eintragen; bis dahin die Preview-URL des PRs nutzen.
- Ablauf (SIN-1385): Preview-URL öffnen → ohne Anmeldung Weiterleitung auf `/login` → mit dem Testkonto anmelden → Weiterleitung auf `/mediathek` → Mediathek, Highlights, Aufträge, Freigabe & Export per Seitenleiste oder Tab/Enter durchgehen (jeder Bereich zeigt einen ehrlichen Leerzustand, keine Beispieldaten) → „Abmelden“ → zurück auf `/login`. `/api/health` bleibt offen, Antwort `{"status":"ok"}`.
- Profil (SIN-1386): angemeldet in der Kopfzeile „Profil“ öffnen (`/profil`) → Nische, Tonalität, Zielgruppe, Hashtags (mit oder ohne `#`, höchstens 30), Plattformen und erlaubte Quellen eintragen → „Profil speichern“: Meldung „Profil gespeichert.“, nach Neuladen stehen die Werte noch da und die Hashtags sind mit `#` normalisiert. Der Schalter „Veröffentlichen erlauben“ ist standardmäßig aus; er ändert nichts an der Freigabepflicht, jede Änderung landet in `social_media.profile_audit`. Mit dem zweiten Testkonto (`sinan-test-2@sjcode.de`) bleibt das Profil leer: es sieht nichts vom ersten. Voraussetzung am gemeinsamen Projekt: Migration `20261105010000_sin1382_creator_profiles.sql` ist eingespielt. Stand 05.11.2026 (Lesezugriff auf `list_tables`/`list_migrations`): sie fehlt dort, `migrate.yml` hat mangels Secret `SOCIALMEDIA_DATABASE_URL` nie gelaufen; bis dahin zeigt `/profil` in Vorschau und Produktion nur „Das Profil konnte gerade nicht geladen werden“.
- Testzugang: Sinans Testkonto (`TESTNUTZER_EMAIL` / `TESTNUTZER_PASSWORT` in Infisical `/leitstand`, das Passwort steht nie in Repo oder PR).
- Beispieldaten zum Durchklicken (SIN-1445): `scripts/testzugang.mjs` gibt den Konten `sinan-test@sjcode.de` und `sinan-test-2@sjcode.de` je einen Creator mit Profil, drei Beispiel-Assets (nur Datenbankzeilen, keine Dateien, keine Videos Dritter) und zwei Beispiel-Aufträgen. Es fasst nur diese beiden Konten an, ist idempotent und überspringt Tabellen, die es noch nicht gibt (und nennt sie). Fehlt ein Konto, legt es das Skript mit dem Passwort aus der Umgebung an. Das zweite Konto dient der Prüfung „sieht nichts vom ersten“. Werte kommen aus Infisical `/leitstand` (`TESTNUTZER_PASSWORT`, `TESTNUTZER2_PASSWORT`, dazu `SUPABASE_URL` und `SUPABASE_SERVICE_ROLE_KEY` nur für dieses Skript, nie in der App oder im Repo):
  ```
  npm run testzugang          # befüllen (beliebig oft)
  npm run testzugang:reset    # Beispieldaten beider Konten löschen und neu anlegen (Anfangsstand)
  ```
  Stand: Logik und Idempotenz sind mit einem In-Memory-Ersatz getestet (`scripts/testzugang.test.ts`); der Lauf gegen eine echte Datenbank ist noch nicht belegt. Die App zeigt noch keine Assets- oder Auftragsseiten, gefüllt ist bislang nur die Datenbank.
- Neue Migrationen spielt `.github/workflows/migrate.yml` nach Merge auf `main` ein. Einmalig legt Sinan das GitHub-Secret `SOCIALMEDIA_DATABASE_URL` an: Session-Pooler-URL (GitHub-Runner haben kein IPv6) einer eigenen Rolle, die nur das Schema `social_media` besitzt, `references` auf `auth.users` hat und in `supabase_migrations.schema_migrations` einfügen darf. Ohne Secret schlägt der Workflow sichtbar fehl.

## App lokal
Voraussetzung: Node 22 (wie in `build.yml`); für die Anmeldung zusätzlich Docker und die Supabase CLI (siehe „Datenbank lokal“).

```
supabase start                      # lokale Supabase; `supabase status` zeigt API URL und anon key
cp .env.example .env.local          # NEXT_PUBLIC_SUPABASE_URL und NEXT_PUBLIC_SUPABASE_ANON_KEY eintragen
npm ci
npm run dev                         # http://localhost:3000 -> Weiterleitung auf /login
npm run typecheck && npm test && npm run build
```

Stand: Anmeldung mit Supabase Auth (SIN-1377): Registrierung (`/registrieren`), Login (`/login`), Abmelden, alle anderen Routen nur mit Session (`proxy.ts`; `/api/health` bleibt offen). Beim ersten Aufruf von `/` nach der Anmeldung legt `ensureCreator()` die Zeile in `social_media.creators` an (idempotent, unter RLS). In der App steckt nur der öffentliche anon-Schlüssel, kein Service-Role-Schlüssel. Profil-Seite `/profil` (SIN-1386): serverseitig geprüft (Allowlists und Längen wie in der Datenbank), gespeichert per Server Action unter den Rechten des Nutzers. Die Tests dazu laufen gegen die lokale Supabase, wenn `SUPABASE_TEST_URL` und `SUPABASE_TEST_ANON_KEY` gesetzt sind (`supabase status` zeigt beide; die CI hat keine API und überspringt sie):

```
SUPABASE_TEST_URL=http://127.0.0.1:54321 SUPABASE_TEST_ANON_KEY=<anon key> npm test
```

Sonst weiter nur Gerüst: kein Upload, keine Medienfunktion, kein Deployment. Das lokale Supabase hat E-Mail-Bestätigung aus (`supabase/config.toml`); ist sie am Zielprojekt an, verweist die Registrierung auf `/login` mit Hinweis.

## Worker lokal
Voraussetzungen: [uv](https://docs.astral.sh/uv/) und FFmpeg (`ffmpeg`/`ffprobe` im PATH).

```
cd worker && uv sync && uv run pytest
uv run ruff check . && uv run mypy .
```

Stand: `worker/` enthaelt `probe(path)` (Dauer, Breite, Hoehe per ffprobe), die Medien-Validierung (SIN-1173), die Szenenerkennung (SIN-1165) und den Render-Baustein (SIN-1166). Keine Queue, kein Upload.

Pilot-Pipeline (SIN-1355, SIN-1364, SIN-1077; nur FFmpeg/ffprobe, kein Modell, keine Datenbank-Queue):

```
uv run python -m socialmedia_worker beispiel ./material            # synthetisches Material: 2 Clips mit Schnitten + Ton, 1 Bild
uv run python -m socialmedia_worker analyze clip.mp4 --asset-id a1  # validate → Szenen → Signale → Highlights als JSON (Schema worker/schemas/analysis.v1.json), Exit 2 bei Ablehnung
uv run python -m socialmedia_worker batch ./material/*.mp4 ./material/foto.png --out ./lauf --auftrag pilot-1
uv run python -m socialmedia_worker export --out ./lauf --auftrag pilot-1  # nur nach Freigabe (Exit 3 ohne)
```

`batch` schreibt je Schritt einen Checkpoint (Upload → Highlights → Videoschnitt → Qualitätsprüfung → Freigabe) nach `lauf/checkpoints.jsonl` und, wenn `SUPABASE_ACCESS_TOKEN` (Infisical `/leitstand`) gesetzt ist, in `leitstand.checkpoints` des gemeinsamen Supabase-Projekts; dort zeigt das Leitstand-Cockpit den Lauf unter `/ablauf/<auftrag>` mit Vorschau, und Sinans Klick auf „Freigeben“ ist der Checkpoint, den `export` liest. Artefakt-Links zeigen auf `/artefakt/<auftrag>/…` des Cockpits, also muss `--out` auf dem Cockpit-Rechner unter `~/leitstand-artefakte/<auftrag>` liegen. Ausgabe: `analyse-<asset>.json`, `highlights.json`, `variante-1.mp4`/`.jpg` (Post „Hook zuerst“), `variante-2.mp4`/`.jpg` (Post „chronologisch“), je aus allen Videos und brauchbaren Fotos mit Überblendung (1080×1920, Mittelschnitt, -14 LUFS, ohne Untertitel und Musik), `pruefung.json` (ffprobe-Abnahme: Format, Dauer ±0,5 s, Cover), `batch.json`; nach Freigabe `export/`. Belegter Lauf und Messwerte: `docs/E2E.md`. Nicht enthalten: Untertitel (SIN-1357), Karussell, Subjektverfolgung, Upload über die App, echtes Creator-Material (SIN-1417).

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

`detect_scenes` ruft `ffmpeg` (scene-Filter) als Subprozess auf. Bewiesen ist es nur an einem zur Laufzeit erzeugten Testclip mit einem harten Schnitt (`worker/tests/test_scenes.py`); wie gut die Erkennung auf echtem Material und mit dem Schwellwert 0,3 arbeitet, ist nicht gemessen. 
Highlight-Auswahl (deterministisch, ohne Modell):

```python
from socialmedia_worker.highlights import select_highlights

manifest = select_highlights("asset-1", segments, signals, min_len=3.0, max_len=30.0, top_n=3)
print(manifest.to_json())  # validiert gegen worker/schemas/highlights.v1.json
```

`signals` hat einen Wert je Segment (z. B. Bewegung, 0..1). Segmente unter `min_len` entfallen, längere werden auf die ersten `max_len` Sekunden gekürzt. `confidence` ist eine Heuristik (das begrenzte Signal), keine Aussage über Reichweite oder Viralität. Es gibt keine menschliche Korrektur.

Segment-Signale und Bildqualität (nur FFmpeg-Filter, kein Modell, keine neue Abhängigkeit):

```python
from socialmedia_worker.signals import segment_signals
from socialmedia_worker.quality import image_quality

signals = segment_signals(path, segments)  # [SegmentSignal(start, end, motion, loudness)]
motion = [s.motion for s in signals]       # Eingabe für select_highlights
q = image_quality(Path("foto.jpg"))        # Quality(sharpness, exposure, reasons=["unscharf"])
```

`motion` (0..1): mittlere Luma-Änderung zwischen Frames (`signalstats` YDIF), geteilt durch 20, begrenzt auf 1. `loudness` (0..1): `volumedetect`-Mittelpegel, linear von -60 dBFS (0) bis 0 dBFS (1); ein Video ohne Tonspur liefert `None`, eine stumme Spur 0. `image_quality` liefert `sharpness` (Kantendichte nach `edgedetect`), `exposure` (Abstand der mittleren Helligkeit von Mittelgrau) und `reasons` ("unscharf", "unterbelichtet", "überbelichtet"); es gilt für JPEG/PNG und für einen mit `extract_cover` gezogenen Frame. Beide prüfen die Quelle vorher mit `validate_media`. Teilstand: reine Heuristik, nur an zur Laufzeit erzeugten Testclips und -bildern belegt (`worker/tests/test_signals.py`, `test_quality.py`); die Skalen sind nicht an echtem Material kalibriert (ein scharfes, aber flächiges Bild kann als „unscharf“ gelten), und es gibt keine Aussage über Reichweite oder Viralität. Noch nicht angebunden: kein Job, der Signale berechnet und an `select_highlights` übergibt.

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
