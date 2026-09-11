import manber_myers


def brute_force_suffix_array(s):
    """Reference implementation: sort suffix start indices by the suffix itself."""
    return sorted(range(len(s)), key=lambda i: s[i:])


def brute_force_lcp_array(s, sa):
    """Reference implementation: for each adjacent pair in the suffix array,
    count the length of their shared prefix."""
    n = len(s)
    lcp = [0] * n
    for i in range(n - 1):
        a, b = s[sa[i]:], s[sa[i + 1]:]
        k = 0
        while k < len(a) and k < len(b) and a[k] == b[k]:
            k += 1
        lcp[i] = k
    return lcp


def test_suffix_array_banana():
    assert manber_myers.suffix_array_ManberMyers("banana") == [5, 3, 1, 0, 4, 2]


def test_suffix_array_matches_brute_force():
    for s in ["mississippi", "abcabxabcd", "aaaaaa", "abcdefg", "banana$"]:
        assert manber_myers.suffix_array_ManberMyers(s) == brute_force_suffix_array(s)


def test_suffix_array_empty_string():
    assert manber_myers.suffix_array_ManberMyers("") == []


def test_suffix_array_single_char():
    assert manber_myers.suffix_array_ManberMyers("a") == [0]


def test_lcp_array_banana():
    sa = manber_myers.suffix_array_ManberMyers("banana")
    assert manber_myers.lcp_array("banana", sa) == [1, 3, 0, 0, 2, 0]


def test_lcp_array_matches_brute_force():
    for s in ["mississippi", "abcabxabcd", "aaaaaa", "abcdefg"]:
        sa = manber_myers.suffix_array_ManberMyers(s)
        assert manber_myers.lcp_array(s, sa) == brute_force_lcp_array(s, sa)


def test_lcp_array_no_repeats_is_all_zero():
    s = "abcdefg"
    sa = manber_myers.suffix_array_ManberMyers(s)
    assert manber_myers.lcp_array(s, sa) == [0] * len(s)
