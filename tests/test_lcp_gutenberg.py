import pytest

import lcp_gutenberg as lg


# ---- lcs() : pure longest-common-substring pipeline ----

def test_lcs_finds_shared_run_and_indices():
    a = "abcdefg"
    b = "zzcdefzz"
    subseq, a_index, b_index = lg.lcs(a, b)
    assert subseq == "cdef"
    assert a[a_index:a_index + len(subseq)] == subseq
    assert b[b_index:b_index + len(subseq)] == subseq


def test_lcs_finds_shared_phrase_with_spaces():
    a = "the quick brown fox jumps"
    b = "a very quick brown bear runs"
    subseq, a_index, b_index = lg.lcs(a, b)
    assert subseq == " quick brown "
    assert a[a_index:a_index + len(subseq)] == subseq
    assert b[b_index:b_index + len(subseq)] == subseq


@pytest.mark.xfail(
    raises=IndexError,
    reason="lcs() assumes some common substring exists; texts with zero shared "
           "characters crash instead of returning an empty match (T008)",
)
def test_lcs_no_overlap_returns_empty():
    subseq, a_index, b_index = lg.lcs("abc", "xyz")
    assert subseq == ""


# ---- clean_text() : strips headers, plus older legacy boilerplate ----

def test_clean_text_strips_legacy_boilerplate(monkeypatch):
    boilerplate = "some legal small print content ratios of Etext to header material. ***"
    body = "\n\nActual book content starts here."
    raw = (boilerplate + body).encode()

    monkeypatch.setattr(lg.textget, "get_text_by_id", lambda id: raw)
    monkeypatch.setattr(lg.textget, "strip_headers", lambda raw_book: raw_book)

    assert lg.clean_text(1) == "Actual book content starts here."


def test_clean_text_leaves_normal_text_unchanged(monkeypatch):
    body = "Actual book content, no legacy boilerplate here."
    raw = body.encode()

    monkeypatch.setattr(lg.textget, "get_text_by_id", lambda id: raw)
    monkeypatch.setattr(lg.textget, "strip_headers", lambda raw_book: raw_book)

    assert lg.clean_text(1) == body


# ---- get_ID() / retrieve_titles() : read the real Gutenberg catalog CSV ----

def test_retrieve_titles_returns_nonempty_list():
    titles = lg.retrieve_titles()
    assert isinstance(titles, list)
    assert len(titles) > 0


def test_get_id_known_title():
    title = "The Declaration of Independence of the United States of America"
    assert lg.get_ID(title) == 1


def test_get_id_unknown_title_returns_zero():
    assert lg.get_ID("Definitely Not A Real Gutenberg Title 12345") == 0


# ---- get_lcs() : end-to-end pipeline with clean_text()/get_ID() stubbed out ----

def test_get_lcs_builds_context_around_match(monkeypatch):
    common = "the extraordinary phrase we are testing for"
    a = "A" * 350 + common + "B" * 350
    b = "C" * 350 + common + "D" * 350

    monkeypatch.setattr(lg, "get_ID", lambda title: {"a": 1, "b": 2}[title])
    monkeypatch.setattr(lg, "clean_text", lambda id: {1: a, 2: b}[id])

    subseq, a_lead, a_trail, b_lead, b_trail = lg.get_lcs("a", "b")

    assert subseq == common
    assert a_lead == "..." + "A" * 300
    assert a_trail == "B" * 300 + "..."
    assert b_lead == "..." + "C" * 300
    assert b_trail == "D" * 300 + "..."


def test_get_lcs_invalid_title_returns_error_tuple(monkeypatch):
    monkeypatch.setattr(lg, "get_ID", lambda title: 0)

    result = lg.get_lcs("nonexistent a", "nonexistent b")

    assert result == ("Error, invalid title(s)", "", "", "", "")
