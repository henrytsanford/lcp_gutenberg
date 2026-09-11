# CLAUDE.md

Context for working on LCP_Gutenberg.

## What this is

A small Flask web app that finds the longest common phrase (technically the
longest common *substring*) between any two full texts on Project Gutenberg.
A user picks two book titles from an autocomplete list; the app downloads
both texts, computes the longest common substring via a suffix array, and
displays the phrase with surrounding context from each book.

Built by Henry Sanford, May–Sep 2023. Previously hosted at
`longestcommonphrase.wl.r.appspot.com` on Google Cloud App Engine — that
hosting has since lapsed, so the project is being restarted.

## Architecture

Pipeline: `main.py` → `lcp_gutenberg.py` → `manber_myers.py`

- **`main.py`** — Flask entry point. Single route `/` (GET + POST).
  GET renders the search form with the full title list for autocomplete;
  POST takes two submitted titles, runs the LCS pipeline, and re-renders
  with the result.
- **`lcp_gutenberg.py`** — business logic:
  - `retrieve_titles()` / `get_ID()` / `retrieve_metadata()` — look up titles
    and Gutenberg IDs from the catalog.
  - `clean_text()` — fetches a book's text via `gutenbergpy` and strips
    Gutenberg's boilerplate header/footer.
  - `get_lcs()` / `lcs()` — the end-to-end title→text→longest-common-substring
    pipeline, plus extracting ~300 chars of context around the match in
    both source texts.
  - `update_cache_settings()` — redirects `gutenbergpy`'s cache to a temp
    dir; needed because App Engine's filesystem is read-only outside `/tmp`.
- **`manber_myers.py`** — standalone Manber-Myers suffix array + LCP array
  construction (pure algorithm, no Flask/IO dependencies).
- **`templates/index.html`** / **`static/css/main.css`** — single-page UI;
  jQuery + jQuery UI (loaded via CDN) drive the autocomplete widget.

**No database.** The Gutenberg catalog is a static CSV:
`pg_catalog_cleaned.csv` (tracked in git, ~18MB) is what the app reads at
runtime; `pg_catalog.csv` (gitignored, raw) is the unprocessed source.
There is no `.env` file and no environment-variable configuration.

## Running locally

```
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
python main.py             # dev server on http://127.0.0.1:8080
```

`flask run` also works if `FLASK_APP=main.py` is set (see `.vscode/launch.json`
for the debug config Henry used).

## Deployment status

Not currently deployed anywhere. The old setup was **Google Cloud App
Engine Standard**, `runtime: python38`, served via Gunicorn
(`gunicorn_config.py` sets `timeout=0` to tolerate slow book downloads).
Python 3.8 on App Engine Standard is now deprecated, so the redeploy
target has moved to **Cloud Run** (`T001`, decided 2026-09-10): a
`Dockerfile` (python:3.11-slim, matching the old runtime's dependency
compatibility) builds the app and runs it via
`gunicorn -c gunicorn_config.py main:app`, reading `$PORT` as Cloud Run
requires. `app.yaml` has been removed since it was App Engine-specific.

## Current known issues / in-flight state

The working tree had uncommitted, unfinished edits when this project was
picked back up — don't assume these are intentional finished work:

- `lcp_gutenberg.py`: `clean_text()` computes a `final_book` variable meant
  to strip additional boilerplate some texts contain, but still `return`s
  the old `decoded_book` — the fix is incomplete. Tracked as `T002`.
- `templates/index.html` / `static/css/main.css`: an in-progress addition
  of a placeholder-text ("watermark") jQuery plugin loaded from a
  non-HTTPS third-party CDN (`http://labs.mario.ec/...`) — fragile and
  insecure as a dependency. Tracked as `T003`.

Stray dev artifacts also live in the repo root and aren't part of the app
proper: `LCP_Gutenberg.ipynb` (scratch notebook), `"Package Version.txt"`
(a full pip/conda env dump), and a duplicate `favicon.jpg` (root vs.
`images/`). Tracked as `T005`.

## Conventions

- No test suite exists yet. If adding one, `manber_myers.py` and the LCS
  pipeline in `lcp_gutenberg.py` are pure and self-contained — good
  candidates to cover first with `pytest`.
- No linter/formatter is configured or enforced.
- No CI is configured.

## Task tracking

Outstanding and in-progress work is tracked in `TASKS.md` at the repo
root — check it before starting work, and update it (claim a task, add
new ones, mark things done) as you go.
