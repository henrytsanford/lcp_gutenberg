"""Exploratory scratch script: same pipeline as find_gallery_matches.py but
sampling far more pairs (in parallel across processes, since each pair's
lcs() suffix-array build is CPU-bound and independent), to see if a wider
search turns up better matches. Writes to gallery_data_explore.json, NOT
gallery_data.json. Run manually:

    python find_gallery_matches_explore.py

Only samples from books already present in the local text cache (see
lcp_gutenberg.update_cache_settings), so it never hits the network."""
import functools
import json
import os
import random
from concurrent.futures import ProcessPoolExecutor, as_completed

import lcp_gutenberg
from gallery_match_filters import is_genuine_match, build_subjects_blob

PAIR_COUNT = 1000          # random book pairs to run the real lcs() on
GALLERY_SIZE = 5           # final entries written out
REPORT_SIZE = 15           # top candidates printed to stdout for review
SAMPLE_SEED = 42           # fixed, so reruns pick the same pairs
OUTPUT_PATH = "gallery_data_explore.json"
# Random pairs rarely repeat a book within one worker's chunk, so a growing
# per-chunk cache of every cleaned text mostly just wastes memory across
# concurrent processes; bound it instead of caching the whole chunk's texts.
TEXT_CACHE_SIZE = 8
WORKER_COUNT = min(os.cpu_count() or 1, 4)


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
    raw_author = row["Authors"][0]
    author = lcp_gutenberg._format_author(raw_author)
    subjects = build_subjects_blob(raw_author, row["Subjects"][0], row["Bookshelves"][0])
    return title, author, subjects


def annotate_pairs(pairs, catalog):
    """Attach title/author metadata to each pair, dropping pairs whose books
    aren't in the catalog. Done once, up front, in the main process so
    worker processes never need the (unpicklable-across-workers-cheaply)
    catalog dataframe."""
    annotated = []
    for id_a, id_b in pairs:
        a_meta = lookup_title_author(catalog, id_a)
        b_meta = lookup_title_author(catalog, id_b)
        if a_meta is None or b_meta is None:
            continue
        annotated.append((id_a, id_b, a_meta, b_meta))
    return annotated


def _chunk(items, n_chunks):
    chunks = [[] for _ in range(n_chunks)]
    for i, item in enumerate(items):
        chunks[i % n_chunks].append(item)
    return [c for c in chunks if c]


def _score_chunk(chunk):
    """Runs in a worker process: scores one slice of annotated pairs,
    loading each book's cleaned text through a small bounded cache (LRU,
    not a per-chunk dict) so memory stays flat regardless of chunk size."""
    lcp_gutenberg.update_cache_settings()
    clean_text_cached = functools.lru_cache(maxsize=TEXT_CACHE_SIZE)(lcp_gutenberg.clean_text)
    results = []
    for id_a, id_b, a_meta, b_meta in chunk:
        text_a = clean_text_cached(id_a)
        text_b = clean_text_cached(id_b)

        subseq, a_lead, a_trail, b_lead, b_trail = lcp_gutenberg.build_match_context(
            text_a, text_b
        )
        if not is_genuine_match(subseq, a_meta, b_meta):
            continue

        a_title, a_author, _ = a_meta
        b_title, b_author, _ = b_meta
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


def score_candidates_parallel(annotated_pairs, worker_count):
    chunks = _chunk(annotated_pairs, worker_count)
    results = []
    done = 0
    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        futures = [executor.submit(_score_chunk, c) for c in chunks]
        for future in as_completed(futures):
            results.extend(future.result())
            done += 1
            print(f"  ...{done}/{len(chunks)} worker chunks done")
    return results


def main():
    lcp_gutenberg.update_cache_settings()
    catalog = lcp_gutenberg.retrieve_metadata()

    ids = cached_ids()
    print(f"Found {len(ids)} cached books.")
    pairs = sample_pairs(ids, PAIR_COUNT, SAMPLE_SEED)
    print(f"Sampled {len(pairs)} random pairs.")

    annotated_pairs = annotate_pairs(pairs, catalog)
    print(f"{len(annotated_pairs)} pairs have catalog metadata for both books.")

    print(f"Scoring across {WORKER_COUNT} worker processes...")
    results = score_candidates_parallel(annotated_pairs, WORKER_COUNT)
    print(f"{len(results)} of {len(annotated_pairs)} pairs had a non-artifactual match.")

    results.sort(key=lambda r: len(r["subseq"]), reverse=True)

    print(f"\nTop {min(REPORT_SIZE, len(results))} candidates:")
    for r in results[:REPORT_SIZE]:
        a, b = r["book_a"], r["book_b"]
        snippet = r["subseq"].replace("\n", " ")
        if len(snippet) > 120:
            snippet = snippet[:117] + "..."
        print(f"  [{len(r['subseq'])} chars] \"{a['title']}\" by {a['author']} <-> "
              f"\"{b['title']}\" by {b['author']}\n      {snippet!r}")

    results = results[:GALLERY_SIZE]

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote {len(results)} matches to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
