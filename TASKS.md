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

- [ ] T020 — Optimize find_gallery_matches.py's candidate-selection algorithm to scale to a much larger pool of book pairs instead of 25 random ones, and add an "interestingness" ranking (rarity + cross-author novelty + result diversity) on top of the existing genuine-match filter (owner: Claude/lcp-gutenberg-e5, started: 2026-09-12) — initially built a shingle-overlap prefilter to rank which pairs got the real lcs() pipeline, but its top picks were mostly quotation artifacts (biographies/anthologies sharing many literal shingles with their subject by design, not by coincidence), so the prefilter was scrapped in favor of pure random pair sampling (scaled to 10,000 pairs, with a --pairs/--smoke-test CLI option for smaller test runs) scored in parallel across 4 worker processes; the shingle index is now only built after scoring, to feed the exclusivity signal in the interestingness ranking. Coordinating with expand-gallery-match-search, which owns gallery_match_filters.py's accept/reject logic.

## Backlog

## Done

Completed tasks are archived in `TASKS_ARCHIVE.md` (currently through T019).
