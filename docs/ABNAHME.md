# Acceptance and evidence matrix

| Gate | Test / evidence | Status |
| --- | --- | --- |
| Repository | README, AGENTS, architecture, roadmap and license decision | Planning |
| Setup | Fresh clone installs and starts on supported environment | Partial: `worker/` installs and tests with `uv sync && uv run pytest` (SIN-1139); app, database and end-to-end start not implemented |
| Upload | Batch of >=2 videos plus >=1 image, validates type/size and ownership | Not implemented |
| Highlights | JSON with asset ID, start/end, confidence and rationale; editable | Not implemented |
| Render | >=2 playable 9:16 drafts with subtitles, cover and caption; inspect actual output | Not implemented (building block `render_vertical`/`extract_cover` exists in `worker/`, SIN-1166: 9:16 cut and cover only; no subtitles, caption, variants or pipeline integration) |
| Reliability | Retry, cancellation, idempotency, duplicate prevention, cost limit | Not implemented |
| Privacy | Isolation tests, upload scanning, deletion, secret redaction | Not implemented |
| Trends | Source/time provenance, access limits, music rights | Not implemented |
| Publishing | Explicit approval, permitted API, duplicate prevention | Not implemented |
| Learning | Authorized metrics, missing data handling, small-sample warnings | Not implemented |
| Leitstand | Authenticated versioned contract and positive/negative E2E probes | Not implemented |

Evidence must include commands, logs (redacted), reproducible test input, output artifact references, and links to CI runs. A passing unit test alone does not establish a live product.
