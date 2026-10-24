# Architecture proposal (not yet implemented)

## Components
- API: Python 3.12+, FastAPI, typed Pydantic request/response schemas.
- Worker: async queue for ingest/analysis/render; retries, idempotency keys, job progress, cancellation and cost accounting.
- Media: FFmpeg/ffprobe baseline; optional scene detector, ASR and embeddings behind versioned adapters; CPU fallback; GPU optional.
- Storage: creator-isolated object storage, immutable originals, derived media, retention and deletion policies.
- Persistence: PostgreSQL (Supabase candidate), row-level isolation, migrations, auditable job/post/event history.
- UI: optional Next.js dashboard for upload, preview, human review and export.
- Optional adapters: OpenShorts, Postiz, OpenNolan, PhotoCraft/FilmCraft/SoundCraft, Voicebox — none selected until verified audit.
- Observability: structured logs without PII/secrets, job traces, errors, render times, model costs and audit events.

## Trust boundaries
Creator user -> authenticated API -> scoped storage/DB -> worker -> artifacts -> human approval -> publishing adapter.
Leitstand -> signed/versioned task API with scoped service identity. No direct database superuser access or shared provider tokens.

## Contract sketch
POST /v1/jobs (Idempotency-Key) -> {job_id,status}; GET /v1/jobs/{id} -> {status,progress,artifacts,error}; POST /v1/jobs/{id}/cancel; POST /v1/artifacts/{id}/approve; GET /v1/health.
Job input: creator_id, asset_ids, output_formats, language, target_platforms, budget_cap. Outputs: original asset IDs, clip start/end timestamps, confidence, rationale, versioned pipeline, URLs with expiry, costs, rights/approval state. Treat this as a proposed contract, not an existing endpoint.

## Delivery
Develop standalone first. Leitstand integration only after independent smoke tests and auth review. No direct webhook that triggers publishing without approval.
