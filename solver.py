import numpy as np
from config import INITIAL_ANCHORS
from utils import is_too_similar_fast

class SemantleSolver:
    def __init__(self, words, word_vectors, api):
        self.words = words
        self.word_vectors = word_vectors
        self.word_to_idx = {w: i for i, w in enumerate(words)}
        self.api = api
        
        self.checked_indices = set()
        self.valid_indices = []
        self.valid_scores = []
        self.bad_indices = []
        self.tested_words_set = set()
        
        self.best_score = -1.0
        self.best_word = None
        self.stagnant_count = 0

    def run_phase_1(self):
        print("=== PHASE 1: Sampling Initial Anchors ===")
        for anchor in INITIAL_ANCHORS:
            if anchor in self.word_to_idx:
                idx = self.word_to_idx[anchor]
                self.checked_indices.add(idx)
                self.tested_words_set.add(anchor)
                
                sim = self.api.get_similarity(anchor)
                if sim is not None and sim > 0:
                    self.valid_indices.append(idx)
                    self.valid_scores.append(sim)
                    print(f"Anchor: '{anchor:<8}' | API Score: {sim:.2f}")

        if not self.valid_scores:
            print("[ERROR] Could not retrieve scores for anchors.")
            return False

        self.best_score = max(self.valid_scores)
        self.best_word = self.words[self.valid_indices[np.argmax(self.valid_scores)]]
        print(f"\n[HOTSPOT FOUND] Top anchor: '{self.best_word}' with score {self.best_score:.2f}%\n")
        return True

    def run_phase_2(self, max_attempts=80):
        print("=== PHASE 2: Dynamic Focused Exploitation (Targeting 100%) ===")
        attempt = 1

        while attempt <= max_attempts and self.best_score < 100.0:
            
            # תרחיש א': ציון 80%+ - טיפוס הרים מקומי צמוד (ללא דחייה וללא בריחה)
            if self.best_score >= 80.0:
                best_idx = self.valid_indices[np.argmax(self.valid_scores)]
                best_vec = self.word_vectors[best_idx]
                scores = np.dot(self.word_vectors, best_vec)

            # תרחיש ב': ציון מתחת ל-80% - חיפוש מבוסס משיכה ודחייה
            else:
                scores_arr = np.array(self.valid_scores, dtype=np.float32)
                temp = 5.0 if self.best_score >= 60.0 else 9.0
                weights = np.exp(scores_arr / temp)
                weights /= np.sum(weights)

                anchor_vecs = self.word_vectors[self.valid_indices]
                v_target_est = np.dot(weights, anchor_vecs)
                norm = np.linalg.norm(v_target_est)
                if norm > 0:
                    v_target_est /= norm

                scores = np.dot(self.word_vectors, v_target_est)

                # הפעלת קנס דחייה אך ורק על אזורים נמוכים
                if self.bad_indices:
                    bad_vecs = self.word_vectors[self.bad_indices]
                    repulsion_scores = np.max(np.dot(self.word_vectors, bad_vecs.T), axis=1)
                    penalty_weight = 0.4 + (self.stagnant_count * 0.1)
                    scores -= penalty_weight * np.maximum(0, repulsion_scores - 0.35)

            # איפוס מילים שנבדקו
            for idx in self.checked_indices:
                scores[idx] = -np.inf

            sorted_candidates_idx = np.argsort(scores)[::-1]

            best_candidate_idx = None
            for cand_idx in sorted_candidates_idx:
                cand_word = self.words[cand_idx]
                if cand_word in self.tested_words_set:
                    continue
                if is_too_similar_fast(cand_word, self.tested_words_set):
                    self.checked_indices.add(cand_idx)
                    continue
                best_candidate_idx = cand_idx
                break

            if best_candidate_idx is None:
                print("[INFO] No more valid candidates found.")
                break

            candidate = self.words[best_candidate_idx]
            self.checked_indices.add(best_candidate_idx)
            self.tested_words_set.add(candidate)

            sim = self.api.get_similarity(candidate)
            if sim is None:
                continue

            if sim > 0:
                self.valid_indices.append(best_candidate_idx)
                self.valid_scores.append(sim)

            if sim > self.best_score:
                diff = sim - self.best_score
                self.best_score = sim
                self.best_word = candidate
                self.stagnant_count = 0
                print(f"Attempt {attempt:02d} | Candidate: '{candidate:<12}' | API Score: {sim:.2f} [NEW BEST! +{diff:.2f}]")
            else:
                self.stagnant_count += 1
                # הוספה ל-bad_indices אך ורק אם הציון נמוך מ-50.0%
                if sim < 50.0:
                    self.bad_indices.append(best_candidate_idx)
                print(f"Attempt {attempt:02d} | Candidate: '{candidate:<12}' | API Score: {sim:.2f}")

            attempt += 1

        if self.best_score >= 100.0:
            print(f"\n[WINNER FOUND] The hidden daily word is: '{self.best_word}'!")