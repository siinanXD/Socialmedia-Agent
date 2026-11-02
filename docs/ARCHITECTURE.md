# Architecture (stack decided 27.10.2026, not yet implemented)

## Components
- API: no separate API service. Next.js (Vercel) server code and Supabase (Auth, PostgREST with RLS, Edge Functions) serve the job contract below.
- Worker: Python 3.12 worker in `worker/` consuming a Supabase queue for ingest/analysis/render; retries, idempotency keys, job progress, cancellation and cost accounting.
- Media: FFmpeg/ffprobe baseline; optional scene detector, ASR and embeddings behind versioned adapters; CPU fallback; GPU optional.
- Storage: separate private Supabase Storage bucket(s) in the same project for creator-isolated immutable originals and derived media, signed URLs, quotas, retention and deletion policies. Do not store video blobs in PostgreSQL.
- Persistence: reuse existing Supabase project `Content-Agent-Lernapp` (project ref `zxielkiwgcgxyudqemjb`) as requested, with a dedicated `social_media` PostgreSQL schema, app-scoped DB privileges, tenant-aware RLS where exposed, separate migration ownership and auditable job/post/event history. Do not modify existing Content Agent / Leitstand tables or schemas without impact assessment.
  - Stand (SIN-1168): `supabase/migrations/20261030010000_*` (Tabellen `creators`, `assets`, `jobs` mit Zustandsregeln per Trigger) und `20261030020000_*` (RLS). `creators.id` ist der `creator_id`; Policies gelten nur für `authenticated` und nur für Zeilen des eigenen Creators, `anon` hat keine Rechte, `service_role` (Worker) umgeht RLS. Originale (`assets`) haben kein UPDATE-Recht und einen Trigger gegen Änderungen; `(creator_id, sha256)` und `(creator_id, idempotency_key)` sind eindeutig. Tests: `supabase/tests/social_media_rls.test.sql` (`supabase test db`). Noch offen: privater Storage-Bucket samt Storage-Policies (liegt in `storage`, eigene Migration), Verknüpfung Job↔Asset, Quoten, Virenscan-Status, Artefakte/Freigabe. Das Schema muss im Projekt unter *API → Exposed schemas* freigeschaltet werden, bevor ein Client es per PostgREST nutzt.
- UI: Next.js app for upload, preview, human review and export.
  - Stand (SIN-1377): Auth über `@supabase/ssr`. `lib/supabase/{server,client}.ts` bauen den Client mit dem anon-Schlüssel und Schema `social_media`; `proxy.ts` (Next 16) frischt die Session je Request auf und prüft sie mit `auth.getUser()` beim Auth-Server (nie nur das Cookie). Nicht angemeldete Nutzer gehen auf `/login`; offen sind `/login`, `/registrieren` und `/api/health`. Server Actions (`lib/auth/actions.ts`) melden an, registrieren und ab; Fehler laufen nur als fester Code in die URL, Rohmeldungen von Supabase werden nicht angezeigt. `ensureCreator()` (`lib/auth/creator.ts`) legt unter RLS (`creators_insert_own`) je Login genau einen Creator an. Die App kennt keinen Service-Role-Schlüssel. Voraussetzung am Zielprojekt: Schema `social_media` unter *Exposed schemas* freigeschaltet (SIN-1412), Auth-URLs gesetzt. Noch offen: Passwort-Reset, Rate-Limit-Einstellungen am Zielprojekt, E-Mail-Bestätigung (Zustand im Zielprojekt klären).
- Optional adapters: nach `docs/UPSTREAM_AUDIT.md` (SIN-1138) ist keiner der sieben Kandidaten gewaehlt; nur Voicebox bleibt als optionaler Wrapper fuer Phase 2 vorgemerkt. FFmpeg/ffprobe ist die Basis.
- Observability: structured logs without PII/secrets, job traces, errors, render times, model costs and audit events.

## Trust boundaries
Creator user -> authenticated API -> scoped storage/DB -> worker -> artifacts -> human approval -> publishing adapter.
Leitstand -> signed/versioned task API with scoped service identity. No direct database superuser access or shared provider tokens.

## Contract sketch
POST /v1/jobs (Idempotency-Key) -> {job_id,status}; GET /v1/jobs/{id} -> {status,progress,artifacts,error}; POST /v1/jobs/{id}/cancel; POST /v1/artifacts/{id}/approve; GET /v1/health.
Job input: creator_id, asset_ids, output_formats, language, target_platforms, budget_cap. Outputs: original asset IDs, clip start/end timestamps, confidence, rationale, versioned pipeline, URLs with expiry, costs, rights/approval state. Implemented as Supabase tables/RPCs with RLS (signed Edge Function for Leitstand), not as FastAPI routes. Treat this as a proposed contract, not an existing endpoint.

## Delivery
Develop standalone first. Leitstand integration only after independent smoke tests and auth review. No direct webhook that triggers publishing without approval.
