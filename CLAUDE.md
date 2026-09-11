# CLAUDE.md

Context for working on LCP_Gutenberg.

## What this is

Flask app finding the longest common substring between two Project Gutenberg texts.
User picks two titles from autocomplete; app downloads both texts, computes the LCS
via a suffix array, shows the phrase with context from each book.

## Architecture

`main.py` (Flask route `/`, GET+POST) → `lcp_gutenberg.py` (title/ID lookup,
`clean_text()` fetch + strip boilerplate, `get_lcs()`/`lcs()` pipeline) →
`manber_myers.py` (pure suffix array + LCP array algorithm). UI is `templates/
index.html` / `static/css/main.css` (jQuery UI via CDN).

No database — reads `pg_catalog_cleaned.csv` (tracked, ~18MB) at runtime;
`pg_catalog.csv` is gitignored raw source. No `.env`/env-var config.

## Running locally

```
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt && python main.py   # http://127.0.0.1:8080
```

## Deployment

Live on **Cloud Run**: `Dockerfile` (python:3.11-slim) runs
`gunicorn -c gunicorn_config.py main:app`, reading `$PORT`. CI (`.github/workflows/ci.yml`)
runs pytest and a Docker build on push/PR to `main`.

## Git & conventions

- Never `git commit`/`git push` or change repo/remote state — Henry handles that himself.
- Don't change what's shown in the gallery (which matches/books appear in `gallery_data.json`,
  or `find_gallery_matches.py`'s sampling/filtering) unless explicitly asked — regenerating it
  is a one-off manual step, not something to redo incidentally while touching gallery code.
- Keep diffs minimal: change only what's needed, don't reformat or restructure untouched code.
- Comments: concise, non-temporal — current behavior only, never "added for X"/"fixed Y"/task
  or issue references.
- No linter/formatter configured.

## Task tracking

Active work in `TASKS.md`, completed history in `TASKS_ARCHIVE.md` (both at repo root) —
check before starting, update as you go.
