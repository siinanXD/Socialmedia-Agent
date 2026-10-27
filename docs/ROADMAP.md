# Delivery plan and dependency gates

## Phase 0 — Inventory and evidence
- Reconcile Linear SIN-1077, SIN-834, SIN-857–860, GitHub repositories, Gedächtnis, existing Content Agent functionality.
- Evaluate OpenShorts, Postiz, OpenNolan, ShortGPT, Craft apps and Voicebox with verified license, last commit, API/CLI, test evidence, GPU, cost and security.
- Record adopt/wrap/reject decisions; avoid duplicate code.

## Phase 1 — Real standalone MVP
- Repo hygiene: Python packaging, CI lint/type/test, security checks, sample env, docker compose where justified.
- Multi-file upload and per-creator media metadata; job state machine, storage isolation and quotas.
- Scene detection and explainable highlight selection with file/timestamps; export machine-readable manifest.
- FFmpeg vertical rendering of two variants, captions/subtitles and covers; real sample test fixtures with rights.
- Minimal preview/download/approval UI; failure handling, retries and cancellation.
- Run a real end-to-end test; document output artifacts and CPU costs.

## Phase 2 — Creative intelligence
- Consent-based trend and competitor research adapters with provenance and access limitations.
- Niche-aware hooks, storyboard variants, audio licensing workflow, creative scoring and manual corrections.
- Evaluate against human-labeled samples; measure false positives and time saved.

## Phase 3 — Publishing and learning
- Official/authorized platform APIs; tokens scoped per creator, approval required, idempotent publication.
- Collect accessible insights at 24h/72h/7d, distinguish missing metrics from zero, compare cautious experiments.
- Privacy/deletion/export and multi-creator permissions.

## Phase 4 — Leitstand integration
- Signed job API, service account, webhooks, dispatch policies and evidence schema.
- Demonstrate positive and negative security tests and independent review before autonomous dispatch.
- Preserve manual approvals for posts until explicitly changed.

**Never treat planning as proof of implementation.** No paid deployment, model API, or autonomous publication without permission.
