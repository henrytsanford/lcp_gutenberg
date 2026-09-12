import json
import os

import pytest

import gallery_match_filters as gmf

FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "real_gallery_candidates.json"
)


# ---- normalize_title() ----

@pytest.mark.parametrize("title, expected", [
    ("History of the Decline and Fall of the Roman Empire — Volume 4",
     "history of the decline and fall of the roman empire"),
    ("History of the Decline and Fall of the Roman Empire — Volume 6",
     "history of the decline and fall of the roman empire"),
    ("History of the Decline and Fall of the Roman Empire � Volume 4",
     "history of the decline and fall of the roman empire"),
    ("The Weavers: a tale of England and Egypt of fifty years ago - Volume 2",
     "the weavers: a tale of england and egypt of fifty years ago"),
    ("Some Book, Vol. III", "some book"),
])
def test_normalize_title_strips_volume_suffix(title, expected):
    assert gmf.normalize_title(title) == expected


@pytest.mark.parametrize("title", [
    "The Two Gentlemen of Verona",
    "Poems",
    "A Brief History of the United States",
])
def test_normalize_title_leaves_plain_titles_unchanged(title):
    assert gmf.normalize_title(title) == title.lower()


# ---- is_self_match() ----

def test_self_match_true_for_exact_duplicate_title_and_author():
    assert gmf.is_self_match(
        "The Two Gentlemen of Verona", "Shakespeare, William",
        "The Two Gentlemen of Verona", "Shakespeare, William",
    )


def test_self_match_true_for_different_volumes_same_author():
    assert gmf.is_self_match(
        "History of the Decline and Fall of the Roman Empire � Volume 4",
        "Gibbon, Edward",
        "History of the Decline and Fall of the Roman Empire � Volume 6",
        "Gibbon, Edward",
    )


def test_self_match_false_when_author_differs():
    """Two unrelated books can share a generic title (e.g. "Poems") -
    without also matching on author this would be a false positive."""
    assert not gmf.is_self_match(
        "Poems", "Millay, Edna St. Vincent",
        "Poems", "Mansfield, Katherine",
    )


def test_self_match_false_when_title_differs():
    assert not gmf.is_self_match(
        "History of the Decline and Fall of the Roman Empire � Volume 6",
        "Gibbon, Edward",
        "Under Sail", "Riesenberg, Felix",
    )


@pytest.mark.parametrize("a_author, b_author", [("", ""), ("", "Gibbon, Edward"), ("Gibbon, Edward", "")])
def test_self_match_false_when_author_missing(a_author, b_author):
    assert not gmf.is_self_match("Some Title", a_author, "Some Title", b_author)


# ---- is_boilerplate() / BOILERPLATE_MARKERS ----

@pytest.mark.parametrize("subseq", [
    ". Extensive research did not uncover any evidence that the U.S. "
    "copyright on this publication was renewed.",
    "the Online Distributed Proofreading Team at https://www.pgdp.net",
    "the Online Distributed Proofreading Team",
    " enclosed in _underscores_. Punctuation, hyphenation, and spelling inconsistenc",
    "[Transcriber's Note: The following",
    "Transcriber's note: obvious typos corrected.",
    "Transcriber�s note",  # mojibake curly-apostrophe variant
    "see https://www.gutenberg.org/1/2/3 for the HTML edition",
])
def test_is_boilerplate_catches_known_markers(subseq):
    assert gmf.is_boilerplate(subseq)


@pytest.mark.parametrize("subseq", [
    "much quicker than they would otherwise have",
    "the tears rolled down his cheeks; for he",
    "It must be remembered, however, that the",
    "He that goeth forth and weepeth, bearing precious seed",
])
def test_is_boilerplate_false_for_ordinary_prose(subseq):
    assert not gmf.is_boilerplate(subseq)


# ---- is_genuine_match() ----

GENUINE_META_A = ("The Republic", "Plato", "Political science; Utopias; Justice")
GENUINE_META_B = ("The Young Oarsmen of Lakeview", "Stratemeyer, Edward", "Boats and boating -- Fiction")


def test_genuine_match_accepts_ordinary_coincidental_phrase():
    subseq = "much quicker than they would otherwise have"
    assert gmf.is_genuine_match(subseq, GENUINE_META_A, GENUINE_META_B)


def test_genuine_match_rejects_too_short():
    assert not gmf.is_genuine_match("the and", GENUINE_META_A, GENUINE_META_B)


def test_genuine_match_rejects_too_long():
    subseq = "x" * (gmf.MAX_MATCH_LENGTH + 1)
    assert not gmf.is_genuine_match(subseq, GENUINE_META_A, GENUINE_META_B)


def test_genuine_match_rejects_low_alpha_ratio():
    """Whitespace/punctuation runs (centered-text padding, "* * * *"
    dividers) can coincidentally align between unrelated books far more
    often than real prose does."""
    subseq = "* " * 15
    assert not gmf.is_genuine_match(subseq, GENUINE_META_A, GENUINE_META_B)


def test_genuine_match_rejects_boilerplate():
    subseq = "the Online Distributed Proofreading Team at https://www.pgdp.net"
    assert not gmf.is_genuine_match(subseq, GENUINE_META_A, GENUINE_META_B)


def test_genuine_match_rejects_self_match():
    subseq = "a perfectly ordinary-looking shared phrase of enough length"
    meta_a = ("The Two Gentlemen of Verona", "Shakespeare, William", "Comedies")
    meta_b = ("The Two Gentlemen of Verona", "Shakespeare, William", "Comedies")
    assert not gmf.is_genuine_match(subseq, meta_a, meta_b)


def test_genuine_match_rejects_about_or_anthologizes():
    subseq = "a perfectly ordinary-looking shared phrase of enough length"
    meta_a = ("Lord Jim", "Conrad, Joseph", "Psychological fiction")
    meta_b = ("Joseph Conrad", "Walpole, Hugh", "Conrad, Joseph, 1857-1924")
    assert not gmf.is_genuine_match(subseq, meta_a, meta_b)


# ---- is_about_or_anthologizes() ----

def test_about_or_anthologizes_true_when_title_names_other_authors_surname():
    """A biography's title naming its subject's surname (e.g. "Joseph
    Conrad" by Hugh Walpole, about Joseph Conrad) is a strong signal it
    quotes that author's own work rather than coinciding with it."""
    a_meta = ("Lord Jim", "Conrad, Joseph", "")
    b_meta = ("Joseph Conrad", "Walpole, Hugh", "")
    assert gmf.is_about_or_anthologizes(a_meta, b_meta)
    assert gmf.is_about_or_anthologizes(b_meta, a_meta)


def test_about_or_anthologizes_true_for_person_subject_heading():
    """A Library-of-Congress-style "Surname, First, dates" subject heading
    (e.g. "Victoria, Queen of Great Britain, 1819-1901") marks a book as a
    biography of that person, even when its title/author don't mention the
    other book's author at all (e.g. a Queen Victoria biography quoting
    Shakespeare)."""
    a_meta = ("King Richard II", "Shakespeare, William", "Tragedies")
    b_meta = ("Queen Victoria", "Browne, E. Gordon",
              "Victoria, Queen of Great Britain, 1819-1901; Queens -- Biography")
    assert gmf.is_about_or_anthologizes(a_meta, b_meta)


def test_about_or_anthologizes_true_for_anthology_role_tag():
    """A compiler/editor/commentator role tag (folded into the subjects
    blob by build_subjects_blob()) marks a book as a curated collection,
    e.g. an anthology reprinting a Shakespeare song."""
    a_meta = ("Twelfth Night", "Shakespeare, William", "Comedies")
    b_meta = ("English Songs and Ballads", "Crosland, T. W. H.",
              "Ballads, English -- Texts compiler")
    assert gmf.is_about_or_anthologizes(a_meta, b_meta)


def test_about_or_anthologizes_false_for_two_ordinary_novels():
    a_meta = ("Persuasion", "Austen, Jane", "England -- Social life and customs -- Fiction")
    b_meta = ("A Cathedral Courtship", "Wiggin, Kate Douglas Smith", "Courtship -- Fiction")
    assert not gmf.is_about_or_anthologizes(a_meta, b_meta)


def test_about_or_anthologizes_false_for_fictional_character_subject():
    """A fictional-character subject (no birth/death year) shouldn't be
    mistaken for a real-person biography subject."""
    a_meta = ("The Merry Wives of Windsor", "Shakespeare, William",
              "Falstaff, John, Sir (Fictitious character) -- Drama")
    b_meta = ("Some Other Novel", "Smith, John", "Adventure fiction")
    assert not gmf.is_about_or_anthologizes(a_meta, b_meta)


def test_about_or_anthologizes_false_for_corporate_author_title_collision():
    """A corporate/government "author" like "United States" shouldn't
    false-positive-match any title that happens to contain that phrase."""
    a_meta = ("The Declaration of Independence", "United States",
              "United States. Declaration of Independence")
    b_meta = ("History of the United States", "Smith, John", "United States -- History")
    assert not gmf.is_about_or_anthologizes(a_meta, b_meta)


# ---- build_subjects_blob() ----

def test_build_subjects_blob_extracts_role_tags():
    blob = gmf.build_subjects_blob(
        "Jacobs, Joseph, 1854-1916 [Compiler]; Batten, John Dickson, 1860-1932 [Illustrator]",
        "Fairy tales; Folklore -- India", "Fairy Tales Bookshelf",
    )
    assert "compiler" in blob.lower()
    assert "fairy tales" in blob.lower()


def test_build_subjects_blob_handles_missing_fields():
    assert gmf.build_subjects_blob(None, None, None) == ""


# ---- Regression against a real 1000-random-pair batch ----
#
# tests/fixtures/real_gallery_candidates.json is every match that passed the
# old length/alpha-ratio filters when find_gallery_matches_explore.py sampled
# 1000 random pairs from the local text cache (SAMPLE_SEED=42) - i.e. it's
# exactly the kind of candidate set is_genuine_match() has to sort genuine
# coincidences out of. It was hand-audited: of the 384 candidates, exactly 9
# are artifacts (2 same-work self-matches - a duplicate "Two Gentlemen of
# Verona" transcription and two volumes of Gibbon's "Decline and Fall" -
# plus 7 boilerplate matches on transcriber/proofreading/copyright-renewal/
# printer's-colophon notices); everything else is a genuine short
# coincidental phrase between unrelated books.
KNOWN_ARTIFACT_SUBSTRINGS = (
    "copyright on this publication was renewed",
    "distributed proofreading",
    "enclosed in _underscores_",
    "transcriber",
    "printed in the united states of america",
)


def _load_fixture():
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_real_batch_known_artifacts_are_rejected():
    candidates = _load_fixture()
    artifacts = [
        c for c in candidates
        if any(s in c["subseq"].lower() for s in KNOWN_ARTIFACT_SUBSTRINGS)
        or gmf.is_self_match(c["a_title"], c["a_author"], c["b_title"], c["b_author"])
    ]
    assert len(artifacts) == 9, (
        "expected exactly the 8 hand-audited artifacts in the fixture; if this "
        "changed, the fixture or the audit is out of date"
    )
    for c in artifacts:
        assert not gmf.is_genuine_match(
            c["subseq"], (c["a_title"], c["a_author"], ""), (c["b_title"], c["b_author"], "")
        ), f"known artifact was not rejected: {c['subseq']!r}"


def test_real_batch_over_90_percent_of_matches_are_genuine():
    candidates = _load_fixture()
    kept = [
        c for c in candidates
        if gmf.is_genuine_match(
            c["subseq"], (c["a_title"], c["a_author"], ""), (c["b_title"], c["b_author"], "")
        )
    ]
    genuine_rate = len(kept) / len(candidates)
    assert genuine_rate > 0.90, (
        f"only {genuine_rate:.1%} of the real batch survived filtering as "
        f"genuine ({len(kept)}/{len(candidates)})"
    )


def test_real_batch_does_not_over_filter_hand_audited_genuine_matches():
    """Spot-check a handful of matches manually confirmed genuine (distinct
    unrelated books, ordinary prose) still survive the tightened filters."""
    candidates = {c["subseq"]: c for c in _load_fixture()}
    genuine_snippets = [
        " much quicker than they would otherwise have ",
        " the tears rolled down his cheeks; for he ",
        ", and, after exchanging a few words with the",
        " there was nothing for him to do but to ",
    ]
    for snippet in genuine_snippets:
        c = candidates[snippet]
        assert gmf.is_genuine_match(
            c["subseq"], (c["a_title"], c["a_author"], ""), (c["b_title"], c["b_author"], "")
        ), f"hand-confirmed genuine match wrongly rejected: {snippet!r}"
