from config import MODEL_PATH, VOCAB_LIMIT
from api_client import SemantleAPI
from model_loader import load_vec_model
from solver import SemantleSolver

def main():
    api = SemantleAPI()
    words, word_vectors = load_vec_model(MODEL_PATH, limit=VOCAB_LIMIT)
    
    if words is None:
        return

    print(f"[INFO] Loaded {len(words)} clean words.\n")
    
    solver = SemantleSolver(words, word_vectors, api)
    
    if solver.run_phase_1():
        solver.run_phase_2()

if __name__ == "__main__":
    main()