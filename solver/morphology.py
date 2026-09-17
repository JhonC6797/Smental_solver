"""Hebrew word filtering, stemming and duplicate detection.

The vocabulary comes from Wikipedia, so it is full of transliterated foreign
names and inflected forms that waste API calls. These helpers keep the
vocabulary to words a Semantle answer could plausibly be.
"""

import re

MIN_WORD_LENGTH = 2
MAX_WORD_LENGTH = 8
MIN_STEM_LENGTH = 3

_HEBREW_WORD = re.compile(rf"[א-ת]{{{MIN_WORD_LENGTH},{MAX_WORD_LENGTH}}}")
_PREFIX_LETTERS = re.compile(r"^[המבכלו]+")
_SUFFIX_FORMS = re.compile(r"(ים|ות|י|ה|נו)$")

# Endings that mark transliterated foreign names in Hebrew Wikipedia. Kept
# deliberately short: the original list also held 'זון', 'כר', 'ברג' and
# 'רגי', which reject the ordinary Hebrew words מזון, סוכר, זכר, שכר and ברג.
_FOREIGN_NAME_ENDINGS = ("שטיין", "לאג")

# Prefixes that, on a long word, usually signal a grammatical form rather
# than a dictionary entry. Left unchanged pending measurement (spec §7).
_GRAMMATICAL_PREFIXES = ("ו", "ב", "כ", "ל", "ד")
_GRAMMATICAL_PREFIX_MIN_LENGTH = 6


def is_clean_hebrew(word: str) -> bool:
    """True if the word is plausible as a Semantle answer."""
    if not _HEBREW_WORD.fullmatch(word):
        return False
    if (
        word.startswith(_GRAMMATICAL_PREFIXES)
        and len(word) >= _GRAMMATICAL_PREFIX_MIN_LENGTH
    ):
        return False
    return not word.endswith(_FOREIGN_NAME_ENDINGS)


def get_stem(word: str) -> str:
    """Strip prefix letters and inflection suffixes.

    A strip is applied only when at least MIN_STEM_LENGTH characters survive.
    The letters המבכלו are prefixes in some words and root letters in others,
    so stripping unconditionally turns ממלכה, מלה and בובה into the empty
    string and makes the duplicate filter treat them as one word.
    """
    for pattern in (_PREFIX_LETTERS, _SUFFIX_FORMS):
        stripped = pattern.sub("", word, count=1)
        if len(stripped) >= MIN_STEM_LENGTH:
            word = stripped
    return word


def is_too_similar_fast(candidate: str, tested_words: set[str]) -> bool:
    """True if the candidate is a near-duplicate of something already tried.

    The 3-character prefix rule below is aggressive and is a known suspect,
    but it is left unchanged until the board can measure how much of the
    vocabulary it burns (spec §7).
    """
    candidate_stem = get_stem(candidate)
    for tested in tested_words:
        tested_stem = get_stem(tested)
        if candidate_stem == tested_stem:
            return True
        if len(candidate_stem) >= 3 and len(tested_stem) >= 3:
            if candidate_stem[:3] == tested_stem[:3]:
                return True
        if candidate in tested or tested in candidate:
            return True
    return False
