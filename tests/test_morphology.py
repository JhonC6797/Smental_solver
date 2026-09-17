"""Regression tests for the word filter. Every word named here was verified
to be mishandled by the original implementation."""

import pytest

from solver.morphology import get_stem, is_clean_hebrew, is_too_similar_fast


@pytest.mark.parametrize("word", ["אש", "ים", "יד", "דם"])
def test_two_letter_words_are_accepted(word):
    """The original regex required 3-8 letters, silently dropping two of the
    15 configured anchors. The live API accepts 'אש' and scores it 31.92."""
    assert is_clean_hebrew(word) is True


@pytest.mark.parametrize("word", ["מזון", "חזון", "איזון", "סוכר", "מוכר"])
def test_real_words_are_not_rejected_by_the_suffix_blacklist(word):
    """If the daily answer is 'סוכר', the original solver could never win."""
    assert is_clean_hebrew(word) is True


@pytest.mark.parametrize("word", ["פערלאג", "רובינשטיין"])
def test_transliterated_foreign_names_are_still_rejected(word):
    assert is_clean_hebrew(word) is False


def test_a_foreign_name_is_kept_when_filtering_it_would_cost_a_real_word():
    """'שוחמכר' ends in 'כר', and so do סוכר, מוכר, שכר and זכר. The two
    cannot be separated by suffix, so the cheaper error wins: an extra
    foreign name costs one wasted guess, while rejecting סוכר makes the
    game unwinnable whenever that is the answer."""
    assert is_clean_hebrew("שוחמכר") is True
    assert is_clean_hebrew("סוכר") is True


@pytest.mark.parametrize("word", ["a", "א", "אבגדהוזחט", "שלום!", "test"])
def test_non_words_are_rejected(word):
    assert is_clean_hebrew(word) is False


@pytest.mark.parametrize("word", ["ממלכה", "מלה", "בהמה", "בובה", "מלחמה"])
def test_stem_never_collapses_below_three_characters(word):
    """These all reduced to '' or a 2-char stem, so the duplicate filter
    treated them as the same word."""
    assert len(get_stem(word)) >= 3


def test_distinct_words_get_distinct_stems():
    assert get_stem("ממלכה") != get_stem("בובה")
    assert get_stem("מלה") != get_stem("בהמה")


def test_stem_still_strips_genuine_inflection():
    assert get_stem("ספרים") == get_stem("ספר")


def test_duplicate_detection_catches_inflections():
    assert is_too_similar_fast("ספרים", {"ספר"}) is True


def test_duplicate_detection_allows_unrelated_words():
    assert is_too_similar_fast("מחשב", {"ספר"}) is False
