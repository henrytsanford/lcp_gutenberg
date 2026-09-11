# Tasks

Lightweight issue board for tracking work across sessions/agents. No DB —
just this file.

**Usage:**
- Claim a task by moving it to **In Progress** and adding
  `(owner: <name>, started: YYYY-MM-DD)`.
- Finish a task by moving it into `TASKS_ARCHIVE.md` under **Done**, with
  `(completed: YYYY-MM-DD)` and a summary of what actually changed.
- Add new tasks to **Backlog** with the next unused ID (check both this file
  and `TASKS_ARCHIVE.md` for the highest one used). IDs are never reused,
  even if a task is dropped.

## In Progress

- [ ] T014 — Add a "gallery" page showcasing pre-computed longest-common-phrase matches between books (owner: Henry, started: 2026-09-10) — new `find_gallery_matches.py` (manual, one-off script) samples catalog book IDs (duplicate-title groups + random fill), cheaply ranks pairs by shared text-prefix length, runs the real `lcs()` pipeline on top candidates, and writes results to `gallery_data.json`. New `/gallery` route in `main.py` + `templates/gallery.html` render that static JSON (no network/LCS work at request time). Extracts a `build_match_context()` helper out of `lcp_gutenberg.get_lcs()` so both the live app and the script share the same context-slicing logic.

## Backlog

## Done

Completed tasks are archived in `TASKS_ARCHIVE.md` (currently through T013).
