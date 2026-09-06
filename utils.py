import re

def is_clean_hebrew(word: str) -> bool:
    # אורך מילה תקני למילון (3 עד 8 אותיות)
    if not re.fullmatch(r'[א-ת]{3,8}', word):
        return False
    
    # סינון קידומות שיעבוד/יחס שכיחות שיוצרות מילים לא מילוניות (כמו 'דגאולה', 'ומקס')
    if word.startswith(('ו', 'ב', 'כ', 'ל', 'ד')) and len(word) > 5:
        return False

    # סינון סיומות תעתיק לועזי/שמות פרטיים נפוצים בויקיפדיה (כמו 'שוחמכר', 'פערלאג', 'אוסטין')
    if word.endswith(('רגי', 'זון', 'ברג', 'שטיין', 'לאג', 'כר')):
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


import matplotlib.pyplot as plt

def plot_solver_history(history):
    if not history:
        return

    attempts = [h['attempt'] for h in history]
    scores = [h['score'] for h in history]
    best_scores = [h['best_score'] for h in history]

    plt.figure(figsize=(10, 5))
    
    # ניסיונות רגילים
    plt.plot(attempts, scores, marker='o', linestyle='-', color='#3498db', alpha=0.6, label='Candidate Score')
    
    # שיא מתקדם
    plt.plot(attempts, best_scores, linestyle='--', color='#e74c3c', linewidth=2, label='Best Score So Far')

    # סימון שיאים חדשים
    for h in history:
        if h['is_new_best']:
            plt.plot(h['attempt'], h['score'], marker='*', markersize=12, color='#f1c40f')

    plt.title('Semantle Solver Progress', fontsize=14, fontweight='bold')
    plt.xlabel('Attempt #', fontsize=12)
    plt.ylabel('Similarity Score (%)', fontsize=12)
    plt.ylim(0, 105)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend(loc='upper left')
    plt.tight_layout()
    plt.show()