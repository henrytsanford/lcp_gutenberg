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

- [ ] T002 — Resolve unfinished `clean_text()` change in lcp_gutenberg.py (computes `final_book` but still returns `decoded_book`)
- [ ] T003 — Resolve in-progress watermark plugin (templates/index.html, static/css/main.css): finish it, replace with an HTTPS-hosted alternative, or revert
- [ ] T004 — Add a pytest suite, starting with manber_myers.py (pure suffix-array logic) and the lcp_gutenberg.py LCS pipeline
- [ ] T005 — Clean up stray dev artifacts: LCP_Gutenberg.ipynb, "Package Version.txt", duplicate favicon.jpg
- [ ] T006 — Set up CI (and a Dockerfile if moving off App Engine)

## Done

- [x] T001 — Decide redeploy target: bump App Engine runtime past python38, migrate to Cloud Run, or host elsewhere (completed: 2026-09-10) — chose Cloud Run; added `Dockerfile` + `.dockerignore`, removed `app.yaml`. Also pinned `Werkzeug==2.1.2` in requirements.txt (unpinned, it resolved to a version that broke Flask 2.1.2's import of `url_quote` — image crash-looped on boot until fixed). Verified locally: `docker build` + `docker run` + `curl localhost:8080/` returned HTTP 200 with the full rendered page. Still open: build/push/deploy to an actual Cloud Run service (needs a GCP project — not done in this session), and CI/Dockerfile hardening is tracked separately as T006.
