# Acceptance and evidence matrix

| Gate | Test / evidence | Status |
| --- | --- | --- |
| Repository | README, AGENTS, architecture, roadmap and license decision | Planning |
| Setup | Fresh clone installs and starts on supported environment | Partial: `worker/` installs and tests with `uv sync && uv run pytest` (SIN-1139); Next.js scaffold starts with `npm run dev` and serves `GET /api/health` (SIN-1174), no app function; database and end-to-end start not implemented |
| Upload | Batch of >=2 videos plus >=1 image, validates type/size and ownership | Partial: worker-side type/size/duration/SHA-256 check only (SIN-1173); Schema `social_media.assets` (Hash-Dedup je Creator, MIME/Größe geprüft, unveränderlich, Eigentum per RLS, SIN-1168, pgTAP-Beweis); no upload, virus scan or quota |
| Highlights | JSON with asset ID, start/end, confidence and rationale; editable | Teilweise, Worker-seitig bewiesen (SIN-1355/SIN-1364, 02.11.2026): `analyze_asset` verbindet validate → Szenen → Signale → `select_highlights` je Datei (JSON nach `worker/schemas/analysis.v1.json`, deterministisch, Test `test_pipeline.py`); `batch` wählt die besten Highlights über alle Dateien. Echter Lauf auf dem Server mit synthetischem Material: `docs/E2E.md`. Weiter offen: menschliche Korrektur in der App, echtes Creator-Material |
| Render | >=2 playable 9:16 drafts with subtitles, cover and caption; inspect actual output | Teilweise (SIN-1364, 02.11.2026): `batch` rendert 2 Varianten 1080×1920 H.264/AAC mit Cover aus den besten Highlights und prüft sie per ffprobe (`pruefung.json`); belegt am echten Output auf dem Server (`docs/E2E.md`). Ohne Untertitel (SIN-1357/1358) und ohne Caption (SIN-1359); synthetisches Material, kein Creator-Video |
| Reliability | Retry, cancellation, idempotency, duplicate prevention, cost limit | Partial: `social_media.jobs` mit Zustandsmaschine, Abbruch durch den Eigentümer, eindeutigem `idempotency_key` je Creator und `budget_cap` (SIN-1168, pgTAP); no worker, retry or cost enforcement; Pilot-Pipeline: Checkpoint je Schritt (JSONL + Supabase `leitstand.checkpoints`), Export nur nach Freigabe-Checkpoint, Originale unverändert (Test) |
| Privacy | Isolation tests, upload scanning, deletion, secret redaction | Partial: Isolationstests für `creators`/`assets`/`jobs` (fremder Creator, anonym) und Löschung per Cascade/Delete-Policy in `supabase/tests/social_media_rls.test.sql` (SIN-1168); no upload scanning, no Storage policies, no secret redaction |
| Trends | Source/time provenance, access limits, music rights | Not implemented |
| Publishing | Explicit approval, permitted API, duplicate prevention | Not implemented |
| Learning | Authorized metrics, missing data handling, small-sample warnings | Not implemented |
| Leitstand | Authenticated versioned contract and positive/negative E2E probes | Not implemented |

Evidence must include commands, logs (redacted), reproducible test input, output artifact references, and links to CI runs. A passing unit test alone does not establish a live product.
