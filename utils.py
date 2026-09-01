import re

def is_clean_hebrew(word: str) -> bool:
    if not re.fullmatch(r'[א-ת]{3,10}', word):
        return False
    if word.startswith(('ו', 'ב', 'כ', 'ל')) and len(word) > 5:
        return False
    return True

def get_stem(word: str) -> str:
    clean = re.sub(r'^[המבכלו]+', '', word)
    clean = re.sub(r'(ים|ות|י|ה|נו)$', '', clean)
    return clean

def is_too_similar_fast(candidate: str, tested_words: set) -> bool:
    cand_stem = get_stem(candidate)
    for tested in tested_words:
        test_stem = get_stem(tested)
        if cand_stem == test_stem:
            return True
        if len(cand_stem) >= 3 and len(test_stem) >= 3:
            if cand_stem[:3] == test_stem[:3]:
                return True
        if candidate in tested or tested in candidate:
            return True
    return False