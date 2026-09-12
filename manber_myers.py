"""lcp_array() is adapted from prasoon2211
https://gist.github.com/prasoon2211/cc3f3d5b43a0885c0e7a"""

import numpy
import polars

def suffix_array_ManberMyers(s):
    """Construct a suffix array given a string, via prefix doubling: each
    round sorts suffixes by their (current rank, rank of the suffix k
    characters ahead) pair and refines ranks from that order, doubling k
    until every suffix has a distinct rank."""
    n = len(s)
    if n == 0:
        return []
    if n == 1:
        return [0]

    # Vectorized equivalent of numpy.array([ord(c) for c in s]): encoding to
    # UTF-32 gives one 4-byte little-endian code point per character, read
    # back as uint32 - avoids a Python-level loop over the whole string.
    rank = numpy.frombuffer(s.encode("utf-32-le"), dtype=numpy.uint32).astype(numpy.int64)
    idx = numpy.arange(n)
    k = 1
    while True:
        key2 = numpy.full(n, -1, dtype=rank.dtype)
        if k < n:
            key2[:n - k] = rank[k:]

        order = (
            polars.DataFrame({"idx": idx, "r1": rank, "r2": key2})
            .sort(["r1", "r2"])["idx"]
            .to_numpy()
        )

        sorted_r1 = rank[order]
        sorted_r2 = key2[order]
        boundary = numpy.empty(n, dtype=bool)
        boundary[0] = False
        boundary[1:] = (sorted_r1[1:] != sorted_r1[:-1]) | (sorted_r2[1:] != sorted_r2[:-1])
        new_rank_sorted = numpy.cumsum(boundary)

        if new_rank_sorted[-1] == n - 1:
            return order.tolist()

        rank = numpy.empty(n, dtype=rank.dtype)
        rank[order] = new_rank_sorted
        k *= 2

def lcp_array(s, sa):
    """Construct a longest common prefix array"""
    n = len(s)
    k = 0
    lcp = [0] * n
    rank = numpy.empty(n, dtype=numpy.int64)
    rank[sa] = numpy.arange(n)
    rank = rank.tolist()
    for i in range(n):
        if rank[i] == n-1:
            k = 0
            continue
        j = sa[rank[i] + 1]
        while i + k < n and j + k < n and s[i + k] == s[j + k]:
            k += 1
        lcp[rank[i]] = k
        if k:
            k -= 1
    return lcp
