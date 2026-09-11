# CLAUDE.md

Context for working on LCP_Gutenberg.

## What this is

Flask app finding the longest common substring between two Project Gutenberg texts.
User picks two titles from autocomplete; app downloads both texts, computes the LCS
via a suffix array, shows the phrase with context from each book. Built by Henry
Sanford, May–Sep 2023.

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

## Deployment status

Not currently deployed. Target is **Cloud Run** (`T001`): `Dockerfile` (python:3.11-slim) runs
`gunicorn -c gunicorn_config.py main:app`, reading `$PORT`. `app.yaml` removed (App Engine-specific).

## Known issues

- `T002`: `clean_text()` computes `final_book` but still returns the old `decoded_book`.
- `T003`: in-progress "watermark" jQuery plugin from a non-HTTPS CDN.
- `T005`: stray dev artifacts in repo root (notebook, env dump, duplicate favicon).

## Git & conventions

- Never `git commit`/`git push` or change repo/remote state — Henry handles that himself.
- Keep diffs minimal: change only what's needed, don't reformat or restructure untouched code.
- Comments: concise, non-temporal — current behavior only, never "added for X"/"fixed Y"/task
  or issue references.
- No linter/formatter or CI configured.

## Task tracking

Tracked in `TASKS.md` at repo root — check before starting, update as you go.
