# Architecture (stack decided 27.10.2026, not yet implemented)

## Components
- API: no separate API service. Next.js (Vercel) server code and Supabase (Auth, PostgREST with RLS, Edge Functions) serve the job contract below.
- Worker: Python 3.12 worker in `worker/` consuming a Supabase queue for ingest/analysis/render; retries, idempotency keys, job progress, cancellation and cost accounting.
- Media: FFmpeg/ffprobe baseline; optional scene detector, ASR and embeddings behind versioned adapters; CPU fallback; GPU optional.
- Storage: separate private Supabase Storage bucket(s) in the same project for creator-isolated immutable originals and derived media, signed URLs, quotas, retention and deletion policies. Do not store video blobs in PostgreSQL.
- Persistence: reuse existing Supabase project `Content-Agent-Lernapp` (project ref `zxielkiwgcgxyudqemjb`) as requested, with a dedicated `social_media` PostgreSQL schema, app-scoped DB privileges, tenant-aware RLS where exposed, separate migration ownership and auditable job/post/event history. Do not modify existing Content Agent / Leitstand tables or schemas without impact assessment.
- UI: Next.js app for upload, preview, human review and export.
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
