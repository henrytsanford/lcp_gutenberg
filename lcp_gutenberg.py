import re
import tempfile
import numpy
import polars as pl
import manber_myers
from gutenbergpy import textget
from gutenbergpy.gutenbergcachesettings import GutenbergCacheSettings

DEFAULT_CACHE_DIR = "tmp" # Where to store compressed texts on Google Cloud
CONTEXT_LENGTH = 300 # Number of characters on each side of LCP


def lcs(a, b):
    """Given two strings, return the longest common subsequence, and its index
    in both strings"""
    null_char = '\0'
    s = a + null_char + b
    sa = manber_myers.suffix_array_ManberMyers(s)
    lcp = manber_myers.lcp_array(s, sa)
    # lcp[i] is the shared prefix length between sa[i] and sa[i + 1], so the
    # last entry has no successor to pair with and must be excluded.
    sorted_lcp = numpy.argsort(lcp[:-1])[::-1]
    a_range = list(range(0, len(a)))

    ls_index = None
    for ele in sorted_lcp:
        x = sa[ele]
        y = sa[ele + 1]
        # is this suffix is in both texts?
        if ((x < len(a) and y > len(a)) or
                (x > len(a) and y < len(a))):
            ls_index = ele
            break

    if ls_index is None:
        return '', 0, 0

    n = sa[ls_index]
    n_b = sa[ls_index + 1] #adjacent to the other suffix

    subseq = ''
    suffix_one = s[n:]
    suffix_two = s[n_b:]

    for i in range(min(len(suffix_two), len(suffix_one))):
        if suffix_one[i] != suffix_two[i]:
            break
        subseq += suffix_one[i]
    
    # check which index is in which text before returning
    if(n in a_range):
        a_index = n
        b_index = n_b
    else:
        a_index = n_b
        b_index = n
    b_index = b_index - len(a) - len(null_char)
    return subseq, a_index, b_index

def build_match_context(a, b):
    """Given two already-fetched texts, return the longest common
    subsequence with surrounding context, as (subseq, a_leading_context,
    a_trailing_context, b_leading_context, b_trailing_context)"""
    subseq, a_index, b_index = lcs(a = a, b = b)
    ellipsis = "..."
    a_leading_context = ellipsis + a[a_index - CONTEXT_LENGTH: a_index]
    a_trailing_context = a[a_index + len(subseq): a_index +
                        len(subseq) + CONTEXT_LENGTH] + ellipsis
    b_leading_context = ellipsis + b[b_index - CONTEXT_LENGTH: b_index]
    b_trailing_context = b[b_index +
                        len(subseq): b_index + len(subseq) +
                        CONTEXT_LENGTH] + ellipsis
    return (subseq, a_leading_context, a_trailing_context,
            b_leading_context, b_trailing_context)

def get_lcs(a_title, b_title):
    """Given two titles in the gutenberg database,
    return the longest common subsequence, and the surrounding context,
    for both texts"""
    a_code = get_ID(a_title)
    b_code = get_ID(b_title)
    if(a_code != 0 and b_code !=0):
        a = clean_text(a_code)
        b = clean_text(b_code)
        return build_match_context(a, b)
    else:
        return("Error, invalid title(s)", "", "", "","")

def clean_text(id):
    """Given the ID# of a text, return the text without headers."""
    update_cache_settings()
    raw_book = textget.get_text_by_id(id) # with headers
    clean_book = textget.strip_headers(raw_book) # without headers
    decoded_book = clean_book.decode();
    # Some older texts have additional legal boilerplate before the actual
    # content that strip_headers() doesn't catch; drop everything up to and
    # including it. Texts without this boilerplate are left untouched, since
    # split() on a missing separator just returns the original string.
    final_book = decoded_book.split(sep="content ratios of Etext to header material. ***")[-1]
    return final_book.lstrip()

def get_ID(title):
    """Given the title of a text, retrieve its corresponding Project
    Gutenberg ID#. Return 0 if title is not found."""
    pg_catalog = retrieve_metadata()
    match = pg_catalog.filter(pl.col("cleaned_title") == title)
    if(len(match) > 0):
        return match["Text#"][0]
    else:
        return 0 #Title is not in catalog

def retrieve_metadata():
    """Returns a dataframe with information about title, author, and ID#
    of every text on Project Gutenberg"""
    return pl.read_csv("pg_catalog_cleaned.csv", infer_schema_length=None)

_AUTHOR_ROLE_RE = re.compile(r"\s*\[[^\]]*\]\s*$")

def _format_author(raw):
    """Return a single display-friendly author name from a raw catalog
    Authors field (e.g. "Jefferson, Thomas, 1743-1826"), or "" if missing.
    Keeps only the first of multiple semicolon-separated authors and drops
    trailing role tags (e.g. "[Editor]") and birth/death-year segments."""
    if raw is None:
        return ""
    first = _AUTHOR_ROLE_RE.sub("", raw.split(";")[0].strip())
    parts = first.split(",")
    if len(parts) > 1 and re.search(r"[\d?]", parts[-1]):
        parts = parts[:-1]
    return ",".join(parts).strip()

def retrieve_titles():
    """Returns a list of {"title": ..., "author": ...} dicts for every text
    on Project Gutenberg. author is "" when missing from the catalog."""
    pg_catalog = retrieve_metadata()
    return [
        {"title": title, "author": _format_author(author)}
        for title, author in zip(pg_catalog["cleaned_title"], pg_catalog["Authors"])
    ]

def update_cache_settings():
    """The text file cache must be written a temporary directory because
      everything else is read only on Google Cloud. In the future, consider
      downloading all the compressed texts before deploying."""
    tempdir = tempfile.tempdir
    if tempdir is None:
        tempdir = DEFAULT_CACHE_DIR
    GutenbergCacheSettings.set(TextFilesCacheFolder=tempdir, 
                               CacheUnpackDir=tempdir)
    
    