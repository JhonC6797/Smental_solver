"""Compare candidate 3D projections and print the numbers.

Position on the board is radius (from the score, exact) plus direction
(from meaning). Direction compresses 300 dimensions onto a sphere's two
degrees of freedom, and the choice decides whether related words actually
land near each other. This script settles it with numbers.

Local MDS from the spec is deliberately excluded: it depends on the guess
order of a live run, so it cannot be scored against a fixed vocabulary.

Run: python -m scripts.measure_projection
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from solver.vocabulary import Vocabulary, load_vocabulary

SAMPLE_PAIRS = 20000
SAMPLE_WORDS = 300
NEIGHBOURS = 20
RANDOM_SEED = 0
LANDMARK_SHARPNESS = 8.0

LANDMARK_WORDS = [
    "בית", "מלחמה", "ספר", "אוכל", "אדם", "מחשב", "מדינה", "ארץ",
    "שמיים", "אש", "ים", "שיר", "חוק", "נסיעה", "רופא", "כסף",
    "ילד", "מים", "זמן", "עבודה", "מוזיקה", "צבא", "בריאות", "אהבה",
    "מכונית", "עיר", "חיה", "צמח", "מזון", "לימוד",
]


@dataclass
class LandmarkBasis:
    indices: list[int]
    directions: np.ndarray  # (landmarks, 3), unit rows


def fit_pca_basis(vectors: np.ndarray, components: int = 3):
    """Return (mean, basis) where basis is (dimensions, components)."""
    mean = vectors.mean(axis=0)
    centred = vectors - mean
    _u, _s, vt = np.linalg.svd(centred, full_matrices=False)
    return mean, vt[:components].T


def _fibonacci_sphere(count: int) -> np.ndarray:
    """Evenly spread unit vectors, so landmarks do not clump."""
    indices = np.arange(count, dtype=np.float64) + 0.5
    phi = np.arccos(1 - 2 * indices / count)
    theta = np.pi * (1 + 5**0.5) * indices
    return np.stack(
        [np.cos(theta) * np.sin(phi), np.sin(theta) * np.sin(phi), np.cos(phi)],
        axis=1,
    )


def fit_landmark_basis(vocabulary: Vocabulary, words: list[str]) -> LandmarkBasis:
    present = [w for w in words if w in vocabulary.word_to_index]
    missing = sorted(set(words) - set(present))
    if missing:
        print(f"  (landmarks absent from the vocabulary: {', '.join(missing)})")
    indices = [vocabulary.word_to_index[w] for w in present]
    return LandmarkBasis(indices=indices, directions=_fibonacci_sphere(len(indices)))


def _unit(rows: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(rows, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return rows / norms


def project_pca(vectors: np.ndarray, mean, basis) -> np.ndarray:
    return _unit((vectors - mean) @ basis)


def project_landmarks(vectors: np.ndarray, vocabulary, basis: LandmarkBasis):
    affinity = vectors @ vocabulary.vectors[basis.indices].T
    weights = np.exp(affinity * LANDMARK_SHARPNESS)
    weights /= weights.sum(axis=1, keepdims=True)
    return _unit(weights @ basis.directions)


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    rank_a = np.argsort(np.argsort(a)).astype(np.float64)
    rank_b = np.argsort(np.argsort(b)).astype(np.float64)
    rank_a -= rank_a.mean()
    rank_b -= rank_b.mean()
    return float(rank_a @ rank_b / (np.linalg.norm(rank_a) * np.linalg.norm(rank_b)))


def evaluate(name: str, vocabulary: Vocabulary, projected: np.ndarray) -> None:
    rng = np.random.default_rng(RANDOM_SEED)
    size = len(vocabulary)

    left = rng.integers(0, size, SAMPLE_PAIRS)
    right = rng.integers(0, size, SAMPLE_PAIRS)
    true_similarity = np.sum(
        vocabulary.vectors[left] * vocabulary.vectors[right], axis=1
    )
    board_similarity = np.sum(projected[left] * projected[right], axis=1)
    correlation = _spearman(true_similarity, board_similarity)

    sample = rng.choice(size, SAMPLE_WORDS, replace=False)
    kept = []
    for index in sample:
        true_top = np.argpartition(
            -(vocabulary.vectors @ vocabulary.vectors[index]), NEIGHBOURS + 1
        )[: NEIGHBOURS + 1]
        board_top = np.argpartition(
            -(projected @ projected[index]), NEIGHBOURS + 1
        )[: NEIGHBOURS + 1]
        kept.append(len(set(true_top) & set(board_top)) / NEIGHBOURS)
    recall = float(np.mean(kept))

    print(f"{name:<12} rank correlation {correlation:+.3f}   "
          f"neighbour recall@{NEIGHBOURS} {recall:.1%}")


def main() -> None:
    vocabulary = load_vocabulary()
    print(f"Vocabulary: {len(vocabulary)} words, "
          f"{vocabulary.vectors.shape[1]} dimensions\n")

    mean, basis = fit_pca_basis(vocabulary.vectors)
    evaluate("PCA", vocabulary, project_pca(vocabulary.vectors, mean, basis))

    landmarks = fit_landmark_basis(vocabulary, LANDMARK_WORDS)
    evaluate("Landmarks", vocabulary,
             project_landmarks(vocabulary.vectors, vocabulary, landmarks))

    print("\nHigher is better on both. Pick the winner for server/projection.py.")


if __name__ == "__main__":
    main()
