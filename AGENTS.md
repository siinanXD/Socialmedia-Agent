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
