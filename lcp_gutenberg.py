import tempfile
import numpy
import pandas as pd
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
    sorted_lcp = numpy.argsort(lcp)[::-1]
    a_range = list(range(0, len(a)))

    for ele in sorted_lcp:
        x = sa[ele]
        y = sa[ele + 1]
        # is this suffix is in both texts?
        if ((x < len(a) and y > len(a)) or 
                (x > len(a) and y < len(a))):
            ls_index = ele
            break

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

def get_lcs(a_title, b_title):
    """Given two titles in the gutenberg database,
    return the longest common subsequence, and the surrounding context,
    for both texts"""
    a_code = get_ID(a_title)
    b_code = get_ID(b_title)
    if(a_code != 0 and b_code !=0):
        a = clean_text(a_code) 
        b = clean_text(b_code) 
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
    else:
        return("Error, invalid title(s)", "", "", "","")

def clean_text(id):
    """Given the ID# of a text, return the text without headers."""
    update_cache_settings()
    raw_book = textget.get_text_by_id(id) # with headers
    clean_book = textget.strip_headers(raw_book) # without headers
    return clean_book.decode()

def get_ID(title):
    """Given the title of a text, retrieve its corresponding Project
    Gutenberg ID#. Return 0 if title is not found."""
    pg_catalog = retrieve_metadata()
    query = pg_catalog.query("cleaned_title==@title")
    if(len(query) > 0):
        return query["Text#"].values[0]
    else:
        return 0 #Title is not in catalog
    
def retrieve_metadata():
    """Returns a dataframe with information about title, author, and ID#
    of every text on Project Gutenberg"""
    return pd.read_csv("pg_catalog_cleaned.csv", low_memory=False)

def retrieve_titles():
    """Returns a list of the title of every text on Project Gutenberg"""
    pg_catalog = retrieve_metadata()
    titles = pg_catalog.cleaned_title.to_list()
    return titles

def update_cache_settings():
    """The text file cache must be written a temporary directory because
      everything else is read only on Google Cloud. In the future, consider
      downloading all the compressed texts before deploying."""
    tempdir = tempfile.tempdir
    if tempdir is None:
        tempdir = DEFAULT_CACHE_DIR
    GutenbergCacheSettings.set(TextFilesCacheFolder=tempdir, 
                               CacheUnpackDir=tempdir)
    
    