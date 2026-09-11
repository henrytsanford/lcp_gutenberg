# Tasks

Lightweight issue board for tracking work across sessions/agents. No DB —
just this file.

**Usage:**
- Claim a task by moving it to **In Progress** and adding
  `(owner: <name>, started: YYYY-MM-DD)`.
- Finish a task by moving it to **Done** with `(completed: YYYY-MM-DD)` and
  a one-line summary of what actually changed.
- Add new tasks to **Backlog** with the next unused ID. IDs are never
  reused, even if a task is dropped.

## In Progress

## Backlog
- [ ] T003 — Resolve in-progress watermark plugin (templates/index.html, static/css/main.css): finish it, replace with an HTTPS-hosted alternative, or revert
- [ ] T006 — Set up CI (and a Dockerfile if moving off App Engine)
- [ ] T008 — Fix `lcs()` in lcp_gutenberg.py: raises `IndexError` instead of returning a sane empty result when the two input texts share no common substring at all (found while adding pytest coverage for T004; not expected in practice for real book texts, which always share incidental characters, but the crash is real for arbitrary input)

## Done

- [x] T002 — Resolve unfinished `clean_text()` change in lcp_gutenberg.py (computes `final_book` but still returns `decoded_book`) (completed: 2026-09-10) — `clean_text()` now splits on the legacy `"content ratios of Etext to header material. ***"` marker, keeps the last segment (the piece after it, or the whole text unchanged if the marker isn't present), strips leading whitespace, and returns that instead of the un-split `decoded_book`. Added `test_clean_text_strips_legacy_boilerplate` and `test_clean_text_leaves_normal_text_unchanged` to `tests/test_lcp_gutenberg.py` (textget calls monkeypatched to avoid network I/O). Full suite: 16 passed, 1 xfailed (T008, unrelated).
- [x] T005 — Clean up stray dev artifacts: LCP_Gutenberg.ipynb, "Package Version.txt", duplicate favicon.jpg (completed: 2026-09-10) — deleted `LCP_Gutenberg.ipynb` and `Package Version.txt` (both already gitignored, untracked); verified root `favicon.jpg` was byte-identical (MD5 match) to `images/favicon.jpg` and unreferenced (`templates/index.html` only points at `images/favicon.jpg`), then `git rm`'d the root copy.
- [x] T004 — Add a pytest suite, starting with manber_myers.py (pure suffix-array logic) and the lcp_gutenberg.py LCS pipeline (completed: 2026-09-10) — added `tests/test_manber_myers.py` (suffix array + LCP array, checked against a brute-force reference and the classic "banana" example) and `tests/test_lcp_gutenberg.py` (`lcs()` against crafted string pairs, `get_ID()`/`retrieve_titles()` against the real `pg_catalog_cleaned.csv`, and `get_lcs()`'s context-window logic with `get_ID`/`clean_text` monkeypatched to avoid network/Gutenberg I/O). Added `pytest.ini` (`pythonpath = .`, `testpaths = tests`) and `requirements-dev.txt` (adds `pytest` on top of `requirements.txt`); installed both into `venv` and ran `pytest -v` — 14 passed. Found `lcs()` crashes with `IndexError` on texts with zero shared characters (not expected for real book text, but a real gap); left it uncovered by the fix and instead added an `xfail` test documenting it, tracked separately as T008.
- [x] T007 — Fix broken/unstyled page on live Cloud Run URL, stuck loading icon (completed: 2026-09-10) — `templates/index.html` built the CSS `<link>` via `url_for('static', filename='/css/main.css')`; the leading slash produced `/static//css/main.css`, which Flask 308-redirects to the single-slash path. Harmless on localhost, but on Cloud Run (TLS terminated at the proxy, no `ProxyFix`) Flask doesn't see the original request as HTTPS, so the redirect's `Location` came back as `http://...` — browsers block that as mixed content on an HTTPS page, so the CSS never loaded at all. That's why the page looked "raw"/unstyled and the loading GIF (only hidden via a CSS rule) stayed stuck visible. Fix: dropped the leading slash so the URL resolves directly with no redirect. Verified locally: `/static/css/main.css` now returns 200 with no redirect.
- [x] T001 — Decide redeploy target: bump App Engine runtime past python38, migrate to Cloud Run, or host elsewhere (completed: 2026-09-10) — chose Cloud Run; added `Dockerfile` + `.dockerignore`, removed `app.yaml`. Also pinned `Werkzeug==2.1.2` in requirements.txt (unpinned, it resolved to a version that broke Flask 2.1.2's import of `url_quote` — image crash-looped on boot until fixed). Verified locally: `docker build` + `docker run` + `curl localhost:8080/` returned HTTP 200 with the full rendered page. Deployed live: created GCP project `lcp-gutenberg`, linked billing, enabled Cloud Run/Cloud Build/Artifact Registry APIs, updated stale `.gcloudignore` to exclude the same dev-artifact/scratch files as `.dockerignore`, and ran `gcloud run deploy` (region `us-central1`, unauthenticated access). Live at https://lcp-gutenberg-qe6v7smvwq-uc.a.run.app — verified HTTP 200 with correct rendered page. CI/Dockerfile hardening is tracked separately as T006.
