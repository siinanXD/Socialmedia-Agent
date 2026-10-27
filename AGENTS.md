# Agent instructions — Socialmedia-Agent

## Product boundary
This repository owns the product. Leitstand coordinates issues, dispatch, reviews and evidence through an explicit integration contract; do not copy Leitstand internals or grant it unrestricted credentials.

## Mandatory preflight
1. Read README.md, docs/PRODUCT.md, docs/ARCHITECTURE.md, docs/ROADMAP.md, docs/ABNAHME.md and Linear SIN-1077, including current comments.
2. Compare current code, tests, PRs, Gedächtnis and Linear. Reuse existing implementation; plan only proven deltas. Check SIN-834 and SIN-857–860.
3. Before adopting third-party tools, verify upstream repository, license, current maintenance, security, API/CLI, infrastructure costs and legal terms. Document source URLs and dated evidence. Never assume an alpha UI has a stable API.
4. Define small isolated tasks with tests and acceptance evidence. Do not silently change auth, secrets, database contracts or publishing policy.

## Safety and quality
- No secrets in commits, prompts, logs, PRs or test fixtures. Least-privilege tokens; creator-level isolation.
- No scraping that bypasses access controls or platform restrictions; no fake engagement.
- Never publish content or spend money without explicit authorization and rights checks. Manual approval is default.
- Keep original uploads immutable; validate MIME/size, enforce quotas, scan uploads, clean temporary data and implement deletion.
- Handle retries idempotently. Never double-post.
- Each change needs tests, documented usage, reproducible setup, and evidence. No "done" without real end-to-end proof.
- Keep README, architecture and Linear updated; report blockers clearly. Do not auto-merge security-sensitive changes.

## Build release and stack (Sinan, 27.10.2026)
- Sinan released the build on 27.10.2026: agents build this product autonomously from Linear project "Socialmedia Agent" (SIN), without asking him. Safety rules above still apply: no publishing, no spending money, no paid services and no production deployment without explicit authorization.
- Building agents use subscriptions only. The product itself may call model APIs, following "LLM in Produkten" in `siinanXD/leitstand-2` `docs/stack.md`: deterministic first, every call traced in Langfuse, prompts in Langfuse Prompt Management, keys with a spend limit in Infisical (Sinan creates the key).
- Stack: Next.js (TypeScript, App Router) on Vercel for UI and server code; Supabase for Auth, Postgres with RLS in schema `social_media`, private Storage, Edge Functions, Queues and pg_cron. No second API layer: the job contract in `docs/ARCHITECTURE.md` is Supabase tables with RLS, plus an Edge Function only where a signed endpoint is needed (Leitstand).
- Python only for FFmpeg/ffprobe media processing: Python 3.12 as a slim worker in `worker/` that consumes a Supabase queue. No FastAPI unless a documented HTTP need exists that Supabase cannot cover; decide that in Linear first. Other reasons for Python: Python-only libraries, jobs >400 s, CPU-heavy work, persistent workers.
- Layout: Next.js app at the repo root (`package.json` + `package-lock.json`), Python worker in `worker/` (`pyproject.toml` + `uv.lock`, dev tools ruff, mypy, pytest), database in `supabase/` (migrations, pgTAP tests in `supabase/tests`). `.github/workflows/build.yml` checks each part as soon as it exists.

## Workflow (Leitstand 2.0)
- One Linear issue, one branch `claude/sin-<nr>-…` or `codex/sin-<nr>-…`, one PR. Title as Conventional Commit with `(SIN-<nr>)`; partial steps with `(Part of SIN-<nr>)`.
- Test first, then code. Smallest diff; build nothing the issue does not ask for; no new dependency for a few lines.
- Subscription access only for agents (Claude, ChatGPT/Codex, Cursor). No model API keys, no API fallback.
- No secrets in the repo. Values come from Infisical (or GitHub secrets); the repo, `.env.example` and docs contain names only.
- Before pushing: `npm run typecheck` and `npm test` green; for `worker/` also `uv run ruff check .`, `uv run mypy .`, `uv run pytest`; for `supabase/` also `supabase test db`.
- Before opening or pushing a PR: answer the self-check in `C:\Dev\AI-Workspace\shared-rules\AI_TOOL_RULES.md` ("Selbstcheck vor jedem PR") for your diff; name open points in the PR.
- Agents exchange results as structured JSON validated against a schema (`claude -p --output-format json --json-schema …`, `codex exec --output-schema …`), never as free text to be parsed.
- Gate (`.github/workflows/gate.yml`, gate code from `siinanXD/leitstand-2` main): squash-merges when `build` is green and Codex has no open findings. Label `risk:low` merges on a green build without Codex review (never for auth, secrets, RLS, publishing or payment changes); `risk:high` for those; `blockiert` stops the gate. Changes under `.github/` are merged by Sinan.
- GitHub/Infisical access follows `docs/github-zugang.md` in leitstand-2; do not create new repository tokens.
