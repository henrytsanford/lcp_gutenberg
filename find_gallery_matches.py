"""One-off script: takes random pairs of already-downloaded books and writes
the best genuine shared-text matches to gallery_data.json for the /gallery
page. Not part of the running app; run manually:

    python find_gallery_matches.py

Only samples from books already present in the local text cache (see
lcp_gutenberg.update_cache_settings), so it never hits the network."""
import json
import os
import random

import lcp_gutenberg

MIN_MATCH_LENGTH = 20      # chars; genuine coincidental phrases between unrelated
                            # books are typically 20-35 chars, so this just discards
                            # single-word matches like "the" or "and the"
MAX_MATCH_LENGTH = 600     # chars; discard near-duplicate-document matches
# Transcriber/production notes (e.g. pointers to an HTML edition or a source
# scan) are common front matter across many texts and aren't real shared
# content; skip matches that are just this boilerplate.
BOILERPLATE_MARKERS = (
    "gutenberg.org", "archive.org", "books.google", "google.com",
    ".htm", ".zip", "Project Gutenberg",
)
# Whitespace runs, "* * * * *" section dividers, and bare headings like
# "CONTENTS" coincidentally align between unrelated books far more often
# than real prose does, so a genuine match needs real letters in it.
MIN_ALPHA_CHARS = 20
MIN_ALPHA_RATIO = 0.5
PAIR_COUNT = 25            # random book pairs to run the real lcs() on
GALLERY_SIZE = 5           # final entries written out
SAMPLE_SEED = 42           # fixed, so reruns pick the same pairs
OUTPUT_PATH = "gallery_data.json"


def cached_ids():
    """Return book IDs already present in the local text cache."""
    tempdir = lcp_gutenberg.tempfile.tempdir or lcp_gutenberg.DEFAULT_CACHE_DIR
    ids = []
    for name in os.listdir(tempdir):
        if name.endswith(".txt.gz"):
            ids.append(int(name[: -len(".txt.gz")]))
    return ids


def sample_pairs(ids, n, seed):
    """Return up to n distinct, unordered (id_a, id_b) pairs sampled from
    ids."""
    rng = random.Random(seed)
    max_pairs = len(ids) * (len(ids) - 1) // 2
    pairs = set()
    while len(pairs) < min(n, max_pairs):
        a, b = rng.sample(ids, 2)
        pairs.add((min(a, b), max(a, b)))
    return list(pairs)


def lookup_title_author(catalog, book_id):
    row = catalog.filter(lcp_gutenberg.pl.col("Text#") == book_id)
    if len(row) == 0:
        return None
    title = row["cleaned_title"][0]
    author = lcp_gutenberg._format_author(row["Authors"][0])
    return title, author


def score_candidates(pairs, catalog):
    full_texts = {}
    results = []
    for id_a, id_b in pairs:
        a_meta = lookup_title_author(catalog, id_a)
        b_meta = lookup_title_author(catalog, id_b)
        if a_meta is None or b_meta is None:
            continue

        for book_id in (id_a, id_b):
            if book_id not in full_texts:
                full_texts[book_id] = lcp_gutenberg.clean_text(book_id)

        subseq, a_lead, a_trail, b_lead, b_trail = lcp_gutenberg.build_match_context(
            full_texts[id_a], full_texts[id_b]
        )
        if len(subseq) < MIN_MATCH_LENGTH or len(subseq) > MAX_MATCH_LENGTH:
            continue
        if any(marker in subseq for marker in BOILERPLATE_MARKERS):
            continue
        letters = sum(1 for c in subseq if c.isalpha())
        if letters < MIN_ALPHA_CHARS or letters / len(subseq) < MIN_ALPHA_RATIO:
            continue

        a_title, a_author = a_meta
        b_title, b_author = b_meta
        results.append({
            "subseq": subseq,
            "book_a": {
                "id": id_a,
                "title": a_title,
                "author": a_author,
                "leading_context": a_lead,
                "trailing_context": a_trail,
            },
            "book_b": {
                "id": id_b,
                "title": b_title,
                "author": b_author,
                "leading_context": b_lead,
                "trailing_context": b_trail,
            },
        })
    return results


def main():
    lcp_gutenberg.update_cache_settings()
    catalog = lcp_gutenberg.retrieve_metadata()

    ids = cached_ids()
    print(f"Found {len(ids)} cached books.")
    pairs = sample_pairs(ids, PAIR_COUNT, SAMPLE_SEED)
    print(f"Sampled {len(pairs)} random pairs.")

    results = score_candidates(pairs, catalog)
    print(f"{len(results)} of {len(pairs)} pairs had a non-artifactual match.")

    results.sort(key=lambda r: len(r["subseq"]), reverse=True)
    results = results[:GALLERY_SIZE]

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote {len(results)} matches to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
