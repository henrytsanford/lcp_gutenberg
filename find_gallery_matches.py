"""One-off script: finds the best genuine shared-text matches across all
already-downloaded books and writes them to review files for manual curation
of the /gallery page. Not part of the running app; run manually:

    python find_gallery_matches.py               # full campaign (10,000 pairs)
    python find_gallery_matches.py --smoke-test   # quick sanity check (100 pairs)
    python find_gallery_matches.py --pairs 500    # custom size

Only uses books already present in the local text cache (see
lcp_gutenberg.update_cache_settings), so it never hits the network.

Candidates are chosen by pure random sampling of book pairs (sample_pairs),
not by ranking pairs on shingle overlap -- shingle-overlap ranking turned out
to systematically favor pairs that share text *on purpose* (e.g. a biography
quoting long passages of its subject's own book) over pairs that share it by
genuine coincidence, wasting the real-lcs() budget on candidates the
genuine-match filter was just going to reject anyway. Pairs whose combined
text exceeds MAX_COMBINED_TEXT_LENGTH are skipped, since a large/repetitive
outlier can make a single lcs() call pathologically slow. Sampled pairs are
scored for real in parallel across WORKER_COUNT worker processes, since each
pair's suffix-array build is CPU-bound and independent.

Because sample_pairs draws deterministically from SAMPLE_SEED, a smaller
--pairs run is a strict prefix of a larger one's sample, not an unrelated
draw -- so --smoke-test is a real preview of the full campaign's pairs.

A shingle index (see SHINGLE_LENGTH/SHINGLE_STRIDE below) is built once up
front and used two ways: as a cheap prefilter, skipping the real lcs() call
entirely for a pair whose books share zero shingles (provably no match is
possible -- see below), and afterward to rank genuine matches found by
rarity/exclusivity in rank_by_interestingness. Unlike the shingle-overlap
*ranking* rejected above, this prefilter only skips a pair already
guaranteed to produce nothing -- it never reorders or prioritizes which of
the randomly sampled pairs get checked, so it doesn't reintroduce the same
bias toward deliberate quotations.

Never writes gallery_data.json -- results go to gallery_data_candidates_*
and gallery_data_review_* files for manual review before hand-curating the
live gallery."""
import argparse
import functools
import json
import os
import random
import time
import zlib
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

import lcp_gutenberg
from gallery_match_filters import (
    is_genuine_match, build_subjects_blob, MIN_MATCH_LENGTH,
)

# Shingle length matches MIN_MATCH_LENGTH, so any match that would pass the
# real filter is guaranteed to contain at least one shingle -- so a pair
# whose books share zero shingles is guaranteed to have no genuine match,
# and can skip the real lcs() call entirely. Sampling every SHINGLE_STRIDE-th
# position (rather than every position) is much cheaper and only risks
# missing matches shorter than SHINGLE_LENGTH + SHINGLE_STRIDE - 1 chars --
# the least interesting ones anyway.
SHINGLE_LENGTH = MIN_MATCH_LENGTH
SHINGLE_STRIDE = 4

GALLERY_SIZE = 5           # final entries in the diverse top pick

DEFAULT_PAIR_COUNT = 10_000   # random book pairs to run the real lcs() on
SMOKE_TEST_PAIR_COUNT = 100   # for --smoke-test: sanity-check before the full run
SAMPLE_SEED = 42               # fixed, so reruns (and smoke tests) draw a consistent,
                                # overlapping sequence of pairs
# A worker process handles many chunks over the run, and random sampling
# repeats book IDs often across chunks (pairs are drawn from a much smaller
# pool of cached books), so the clean_text cache is kept for the worker's
# whole lifetime rather than rebuilt per chunk -- bounded so it doesn't grow
# to hold every cached book's text at once.
# Random sampling has no book-size cap, so an occasional pair combines two
# very large (or, worse, internally repetitive) texts. lcs()'s search for the
# best *cross*-text match has to skip past every same-text internal repeat
# ranked above it, each skip re-slicing and regex-scanning that repeat's
# span -- on a large, repetitive book this can turn one pair into a
# multi-hour outlier. Capping combined length bounds that worst case; the
# cap is generous enough to exclude only the most extreme tail (well under
# 1% of a random sample) of combined lengths.
MAX_COMBINED_TEXT_LENGTH = 4_000_000
TEXT_CACHE_SIZE = 32
# Each worker's suffix-array build on a large pair briefly needs several
# n-sized int64 arrays/lists; four such builds landing concurrently can spike
# total memory past what's available. Capped at 2 rather than cpu_count() to
# keep that peak survivable.
WORKER_COUNT = min(os.cpu_count() or 1, 2)
# Pairs per unit of work handed to a worker and checkpointed. Kept independent
# of WORKER_COUNT so checkpoints land often regardless of how many workers are
# running -- an interrupted run loses at most the chunks in flight, not a
# whole worker's share of the run.
CHECKPOINT_CHUNK_SIZE = 50

# Set once per worker process by _init_worker, not per chunk.
_worker_book_shingles = None
_worker_clean_text = None


def cached_ids():
    """Return book IDs already present in the local text cache."""
    tempdir = lcp_gutenberg.tempfile.tempdir or lcp_gutenberg.DEFAULT_CACHE_DIR
    ids = []
    for name in os.listdir(tempdir):
        if name.endswith(".txt.gz"):
            ids.append(int(name[: -len(".txt.gz")]))
    return ids


def load_all_texts(ids):
    """clean_text() for every cached book, keyed by ID. Loading all of them
    up front (rather than lazily per sampled pair) is what makes the shingle
    index below possible, and is cheap since they're already on disk."""
    return {book_id: lcp_gutenberg.clean_text(book_id) for book_id in ids}


def _book_shingles(text):
    """Deduped shingle hashes for one text, sampled every SHINGLE_STRIDE
    characters. Uses zlib.crc32 rather than the builtin hash() so hash
    values are stable across runs and processes."""
    data = text.encode("utf-8", "ignore")
    n = len(data) - SHINGLE_LENGTH + 1
    if n <= 0:
        return np.array([], dtype=np.uint32)
    hashes = np.fromiter(
        (zlib.crc32(data[i:i + SHINGLE_LENGTH]) for i in range(0, n, SHINGLE_STRIDE)),
        dtype=np.uint32,
    )
    return np.unique(hashes)


def book_shingles_by_id(full_texts):
    """Deduped shingle hash array per book ID (see _book_shingles), keyed
    the same as full_texts. Shared by both the zero-overlap prefilter and
    build_shingle_index's global ranking lookup, so shingles are only
    computed once per book."""
    return {book_id: _book_shingles(text) for book_id, text in full_texts.items()}


def build_shingle_index(per_book_shingles):
    """Build a sorted (hash, book_id) index from precomputed per-book
    shingle sets (see book_shingles_by_id), so "which cached books contain
    this exact shingle" is a binary search away. Returns (sorted_hashes,
    sorted_book_ids)."""
    all_hashes = np.concatenate(list(per_book_shingles.values()))
    all_book_ids = np.concatenate([
        np.full(len(arr), book_id, dtype=np.int32)
        for book_id, arr in per_book_shingles.items()
    ])
    order = np.argsort(all_hashes, kind="stable")
    return all_hashes[order], all_book_ids[order]


def books_sharing_shingle(shingle_hash, sorted_hashes, sorted_book_ids):
    """Distinct book IDs whose sampled shingles include this exact hash."""
    lo = np.searchsorted(sorted_hashes, shingle_hash, side="left")
    hi = np.searchsorted(sorted_hashes, shingle_hash, side="right")
    return np.unique(sorted_book_ids[lo:hi])


def _shingles_overlap(a, b):
    """True iff two sorted, deduped shingle-hash arrays (see
    _book_shingles) share any element. Zero overlap proves no substring of
    length >= SHINGLE_LENGTH + SHINGLE_STRIDE - 1 exists between the two
    texts (see the SHINGLE_LENGTH/SHINGLE_STRIDE comment above)."""
    return np.intersect1d(a, b, assume_unique=True).size > 0


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


def _chunk(items, size):
    """Fixed-size contiguous batches, independent of worker count -- keeps
    checkpoint frequency stable regardless of WORKER_COUNT."""
    return [items[i:i + size] for i in range(0, len(items), size)]


def _init_worker(per_book_shingles):
    """Runs once per worker process (not per chunk): sets up state that
    should persist across every chunk the worker handles."""
    global _worker_book_shingles, _worker_clean_text
    lcp_gutenberg.update_cache_settings()
    _worker_book_shingles = per_book_shingles
    _worker_clean_text = functools.lru_cache(maxsize=TEXT_CACHE_SIZE)(lcp_gutenberg.clean_text)


def _score_chunk(chunk):
    """Runs in a worker process: scores one slice of annotated pairs. A
    pair whose books share no shingle is skipped before any text is loaded
    or lcs() is run, since that's proof no genuine match is possible (see
    _shingles_overlap). Book text is loaded through a cache that persists
    for the worker's whole lifetime (see _init_worker), so a book recurring
    across chunks assigned to this worker is only decompressed/cleaned
    once. Returns (results, skipped_count)."""
    results = []
    skipped = 0
    for id_a, id_b, a_meta, b_meta in chunk:
        if not _shingles_overlap(_worker_book_shingles[id_a], _worker_book_shingles[id_b]):
            skipped += 1
            continue

        text_a = _worker_clean_text(id_a)
        text_b = _worker_clean_text(id_b)
        if len(text_a) + len(text_b) > MAX_COMBINED_TEXT_LENGTH:
            continue

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
    return results, skipped


def score_candidates_parallel(annotated_pairs, worker_count, chunk_size, checkpoint_path,
                               per_book_shingles):
    """Scores every annotated pair across worker_count worker processes,
    rewriting checkpoint_path after each completed chunk so an interrupted
    run doesn't lose everything found so far. Returns (results,
    skipped_total), where skipped_total counts pairs the shingle prefilter
    ruled out before the real lcs() pipeline ran."""
    chunks = _chunk(annotated_pairs, chunk_size)
    results = []
    skipped_total = 0
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=worker_count, initializer=_init_worker,
                              initargs=(per_book_shingles,)) as executor:
        futures = [executor.submit(_score_chunk, c) for c in chunks]
        for i, future in enumerate(as_completed(futures), start=1):
            chunk_results, chunk_skipped = future.result()
            results.extend(chunk_results)
            skipped_total += chunk_skipped
            elapsed = time.perf_counter() - start
            print(f"  ...chunk {i}/{len(chunks)} done "
                  f"({len(results)} genuine so far, {skipped_total} skipped "
                  f"(no shingle overlap), {elapsed:.0f}s elapsed)", flush=True)
            with open(checkpoint_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
    return results, skipped_total


def rank_by_interestingness(results, sorted_hashes, sorted_book_ids):
    """Score genuine matches for how interesting they are: longer passages
    score higher; a phrase shared despite the two books having different
    authors is more surprising than one two books by the *same* author
    happen to share (an authorial habit, not a coincidence); and a phrase
    that's exclusive to just this pair -- not one that also turns up
    elsewhere in the cache under a shingle common enough that is_boilerplate
    happened not to catch it by name -- is more surprising than one that
    doesn't."""
    scored = []
    for r in results:
        subseq = r["subseq"]
        a_author = r["book_a"]["author"]
        b_author = r["book_b"]["author"]
        same_author = bool(a_author) and a_author.strip().lower() == b_author.strip().lower()

        shingle_hash = zlib.crc32(subseq[:SHINGLE_LENGTH].encode("utf-8", "ignore"))
        sharers = len(books_sharing_shingle(shingle_hash, sorted_hashes, sorted_book_ids))
        exclusivity = 1.0 if sharers <= 2 else 2.0 / sharers

        score = len(subseq) * exclusivity * (0.5 if same_author else 1.0)
        scored.append((score, r))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [r for _, r in scored]


def select_diverse(ranked_results, n):
    """Take the top n results, but skip a candidate that reuses a book
    already claimed by a higher-ranked entry, so one especially "chatty"
    pair of books can't crowd out variety in a small gallery. Falls back to
    allowing reuse only if there aren't enough distinct candidates to fill
    the gallery."""
    chosen = []
    used_books = set()
    leftovers = []
    for r in ranked_results:
        ids = {r["book_a"]["id"], r["book_b"]["id"]}
        if ids & used_books:
            leftovers.append(r)
            continue
        chosen.append(r)
        used_books |= ids
        if len(chosen) == n:
            return chosen
    for r in leftovers:
        if len(chosen) == n:
            break
        chosen.append(r)
    return chosen


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, default=DEFAULT_PAIR_COUNT,
                         help=f"number of random pairs to sample (default {DEFAULT_PAIR_COUNT})")
    parser.add_argument("--smoke-test", action="store_true",
                         help=f"shortcut for --pairs {SMOKE_TEST_PAIR_COUNT}, to sanity-check "
                              "the pipeline before committing to a full run")
    return parser.parse_args()


def main():
    args = parse_args()
    pair_count = SMOKE_TEST_PAIR_COUNT if args.smoke_test else args.pairs
    candidates_path = f"gallery_data_candidates_{pair_count}pairs.json"
    review_path = f"gallery_data_review_{pair_count}pairs.json"
    checkpoint_path = f"gallery_data_candidates_{pair_count}pairs.progress.json"

    lcp_gutenberg.update_cache_settings()
    catalog = lcp_gutenberg.retrieve_metadata()

    ids = cached_ids()
    print(f"Found {len(ids)} cached books.", flush=True)

    pairs = sample_pairs(ids, pair_count, SAMPLE_SEED)
    print(f"Sampled {len(pairs)} random pairs.", flush=True)

    annotated_pairs = annotate_pairs(pairs, catalog)
    print(f"{len(annotated_pairs)} pairs have catalog metadata for both books.", flush=True)

    t0 = time.perf_counter()
    full_texts = load_all_texts(ids)
    t1 = time.perf_counter()
    text_lengths = {book_id: len(t) for book_id, t in full_texts.items()}
    print(f"Loaded {len(full_texts)} texts ({sum(text_lengths.values()) / 1e6:.1f}M chars) "
          f"in {t1 - t0:.0f}s.", flush=True)
    per_book_shingles = book_shingles_by_id(full_texts)
    sorted_hashes, sorted_book_ids = build_shingle_index(per_book_shingles)
    print(f"Built shingle index in {time.perf_counter() - t1:.0f}s "
          f"(used to prefilter pairs and rank results).", flush=True)

    print(f"Scoring across {WORKER_COUNT} worker processes...", flush=True)
    results, skipped_total = score_candidates_parallel(
        annotated_pairs, WORKER_COUNT, CHECKPOINT_CHUNK_SIZE, checkpoint_path, per_book_shingles
    )
    genuine_rate = len(results) / len(annotated_pairs) if annotated_pairs else 0.0
    skip_rate = skipped_total / len(annotated_pairs) if annotated_pairs else 0.0
    print(f"Skipped {skipped_total} of {len(annotated_pairs)} pairs ({skip_rate:.1%}) "
          f"with no shingle overlap.", flush=True)
    print(f"{len(results)} of {len(annotated_pairs)} pairs ({genuine_rate:.1%}) "
          f"were genuine matches.", flush=True)

    with open(candidates_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote {len(results)} genuine matches to {candidates_path} for manual review.")

    ranked_results = rank_by_interestingness(results, sorted_hashes, sorted_book_ids)
    final = select_diverse(ranked_results, GALLERY_SIZE)

    print(f"\nTop {len(final)} picks:")
    for r in final:
        a, b = r["book_a"], r["book_b"]
        snippet = r["subseq"].replace("\n", " ")
        if len(snippet) > 120:
            snippet = snippet[:117] + "..."
        print(f"  [{len(r['subseq'])} chars] \"{a['title']}\" by {a['author']} <-> "
              f"\"{b['title']}\" by {b['author']}\n      {snippet!r}")

    with open(review_path, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2)
    print(f"\nWrote {len(final)} matches to {review_path} for manual review "
          f"(gallery_data.json untouched).")


if __name__ == "__main__":
    main()
