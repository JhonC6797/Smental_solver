import os
import numpy as np
from utils import is_clean_hebrew

def load_vec_model(filepath: str, limit: int = 80000):
    if not os.path.exists(filepath):
        print(f"[ERROR] '{filepath}' not found.")
        return None, None

    print(f"[INFO] Loading vector model from '{filepath}'...")
    words = []
    vectors = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        f.readline()  # דילוג על שורת הכותרת
        for line in f:
            if len(words) >= limit:
                break
            parts = line.rstrip().split(' ')
            word = parts[0]
            
            if is_clean_hebrew(word):
                try:
                    vec = np.array([float(x) for x in parts[1:]], dtype=np.float32)
                    words.append(word)
                    vectors.append(vec)
                except ValueError:
                    continue

    vectors = np.array(vectors, dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    
    return words, vectors / norms