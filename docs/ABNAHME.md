# Acceptance and evidence matrix

| Gate | Test / evidence | Status |
| --- | --- | --- |
| Repository | README, AGENTS, architecture, roadmap and license decision | Planning |
| Setup | Fresh clone installs and starts on supported environment | Partial: `worker/` installs and tests with `uv sync && uv run pytest` (SIN-1139); Next.js scaffold starts with `npm run dev` and serves `GET /api/health` (SIN-1174), no app function; database and end-to-end start not implemented |
| Upload | Batch of >=2 videos plus >=1 image, validates type/size and ownership | Partial: worker-side type/size/duration/SHA-256 check only (SIN-1173); Schema `social_media.assets` (Hash-Dedup je Creator, MIME/Größe geprüft, unveränderlich, Eigentum per RLS, SIN-1168, pgTAP-Beweis); no upload, virus scan or quota |
| Highlights | JSON with asset ID, start/end, confidence and rationale; editable | Teilweise (SIN-1167): `select_highlights` im Worker wählt aus Szenen-Segmenten per Heuristik (Signal je Segment, nicht Viralität) und schreibt ein Manifest `worker/schemas/highlights.v1.json` mit Asset-ID, Start/Ende, Confidence, Begründung, Pipeline-Version. Signale (SIN-1353): `segment_signals` (Bewegung, Lautstärke je Segment) und `image_quality` (Schärfe, Belichtung, Gründe) berechnen die Werte aus FFmpeg-Filtern, nur Heuristik, an generierten Testclips belegt, nicht an echtem Material kalibriert, keine Aussage über Viralität. Nicht umgesetzt: menschliche Korrektur/Bearbeitung, Anbindung an Jobs |
| Render | >=2 playable 9:16 drafts with subtitles, cover and caption; inspect actual output | Not implemented (building block `render_vertical`/`extract_cover` exists in `worker/`, SIN-1166: 9:16 cut and cover only; no subtitles, caption, variants or pipeline integration) |
| Reliability | Retry, cancellation, idempotency, duplicate prevention, cost limit | Partial: `social_media.jobs` mit Zustandsmaschine, Abbruch durch den Eigentümer, eindeutigem `idempotency_key` je Creator und `budget_cap` (SIN-1168, pgTAP); no worker, retry or cost enforcement |
| Privacy | Isolation tests, upload scanning, deletion, secret redaction | Partial: Isolationstests für `creators`/`assets`/`jobs` (fremder Creator, anonym) und Löschung per Cascade/Delete-Policy in `supabase/tests/social_media_rls.test.sql` (SIN-1168); no upload scanning, no Storage policies, no secret redaction |
| Trends | Source/time provenance, access limits, music rights | Not implemented |
| Publishing | Explicit approval, permitted API, duplicate prevention | Not implemented |
| Learning | Authorized metrics, missing data handling, small-sample warnings | Not implemented |
| Leitstand | Authenticated versioned contract and positive/negative E2E probes | Not implemented |

Evidence must include commands, logs (redacted), reproducible test input, output artifact references, and links to CI runs. A passing unit test alone does not establish a live product.
