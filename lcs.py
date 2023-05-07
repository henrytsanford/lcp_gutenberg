# Issues: Blank sequence bug
# Need function for subseq given indices

import collections
import numpy
import gutenbergpy
import pandas as pd
import gutenbergpy.textget
import gutenbergpy.gutenbergcachesettings
from gutenbergpy.gutenbergcachesettings import GutenbergCacheSettings
import tempfile

def sort_bucket(s, bucket, order):
    d = collections.defaultdict(list) 
    for i in bucket: 
        key = s[i:i+order] 
        d[key].append(i) 
    result = [] 
    for k,v in sorted(d.items()): 
        if len(v) > 1: 
            result += sort_bucket(s, v, order*2) 
        else: 
            result.append(v[0]) 
    return result 

def suffix_array_ManberMyers(s): 
    return sort_bucket(s, (i for i in range(len(s))), 1)
    
def lcp_array(s, sa):
    n = len(s)
    k = 0
    lcp = [0] * n
    rank = [0] * n
    for i in range(n):
        rank[sa[i]] = i
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

def lcs(a, b):
    null_char = '\0'
    s = a + null_char + b
    a_range = list(range(0, len(a)))
    sa = suffix_array_ManberMyers(s)
    print("making lcp")
    lcp = lcp_array(s, sa)
    sorted = numpy.argsort(lcp)[::-1]

    print("finding duplicates")

    # TODO Instead of searching the array, use a range comparison
    for ele in sorted:
        x = sa[ele]
        y = sa[ele + 1]
        # is this suffix is in both texts?
        if ((x < len(a) and y > len(a)) or 
                (x > len(a) and y < len(a))):
            ls_index = ele
            break
#        if not ((x in a_range and y in a_range) or 
#                (x not in a_range and y not in a_range)):
#            ls_index = ele 

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

def get_lcs(a_code, b_code):
    a = clean_text(a_code) 
    b = clean_text(b_code) 
    print("texts cleaned")
    subseq, a_index, b_index = lcs(a = a, b = b)
    print(subseq)
    a_context = a[a_index - 100: a_index + 100]
    b_context = b[b_index - 100: b_index + 100]
    return subseq, a_context, b_context

def clean_text(id):
    update_cache_settings()
    # This gets a book by its gutenberg id number
    raw_book = gutenbergpy.textget.get_text_by_id(id) # with headers
    clean_book = gutenbergpy.textget.strip_headers(raw_book) # without headers
    return clean_book.decode()

def get_ID(title):
    pg_catalog = retrieve_metadata()
    query = pg_catalog.query("cleaned_title==@title")
    if(len(query) > 0):
        return query["Text#"].values[0]
    else:
        return 0 #Title is not in catalog
    
def retrieve_metadata():
    return pd.read_csv("pg_catalog_cleaned.csv", low_memory=False)

def update_cache_settings():

    # Need to write our cache to a temporary directory because everything else is
    # read only on google
    # The other solution is to download every text: TODO
    tempdir = tempfile.tempdir
    print(tempdir)
    if tempdir is None:
        print("couldn't find tempdir")
        tempdir = "tmp"
    GutenbergCacheSettings.set(TextFilesCacheFolder=tempdir, CacheUnpackDir=tempdir)

