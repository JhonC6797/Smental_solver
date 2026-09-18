"""Turn a word and its score into a position on the board.

Radius comes from the score and is exact: it is the number Semantle
returned, so a point halfway to the centre really is 50%. Direction comes
from the word's meaning, via a PCA basis fitted once at startup, so a word
always lands in the same direction and the board behaves like a map rather
than a re-shuffling cloud.

PCA was chosen by measurement, not taste: against a landmark layout it
scored a rank correlation of +0.425 versus +0.099 (scripts/measure_projection.py).
Neighbour recall is only about 6%, which is the honest limit of compressing
300 dimensions onto a sphere's two degrees of freedom — the board shows
broad semantic regions faithfully, but does not guarantee that two close
synonyms end up adjacent.

The basis is fitted from the vocabulary alone and never from the guesses,
so adding a guess never moves the points already on the board.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from solver.vocabulary import Vocabulary

BOARD_RADIUS = 10.0
_COMPONENTS = 3
BASIS_FILENAME = "projection.npz"

# A vector that projects to zero length has no direction. The fallback is a
# fixed axis rather than a random one, so such a word still lands in the
# same place on every run.
_FALLBACK_DIRECTION = np.array([0.0, 0.0, 1.0])


def fit_basis(vectors: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The mean and the three principal directions of the vocabulary."""
    mean = vectors.mean(axis=0)
    _u, _s, vt = np.linalg.svd(vectors - mean, full_matrices=False)
    return mean, vt[:_COMPONENTS].T


def save_basis(path: Path, mean: np.ndarray, basis: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, mean=mean, basis=basis)


@dataclass(frozen=True)
class Position:
    x: float
    y: float
    z: float
    radius: float


class BoardProjection:
    def __init__(self, vocabulary: Vocabulary, basis_path: Path | None = None) -> None:
        self._vocabulary = vocabulary
        # A stored basis is preferred over fitting one: the signs an SVD
        # returns are not guaranteed to match across library versions, so
        # refitting could mirror the whole board between machines. It also
        # saves a decomposition of the full vocabulary at every startup.
        if basis_path is not None and basis_path.exists():
            stored = np.load(basis_path)
            self.mean_vector, self._basis = stored["mean"], stored["basis"]
        else:
            self.mean_vector, self._basis = fit_basis(vocabulary.vectors)

    def place(self, word: str, similarity: float) -> Position:
        index = self._vocabulary.word_to_index[word]
        return self.place_vector(self._vocabulary.vectors[index], similarity)

    def place_vector(self, vector: np.ndarray, similarity: float) -> Position:
        radius = BOARD_RADIUS * (1.0 - similarity / 100.0)
        point = self._direction(vector) * radius
        return Position(
            x=float(point[0]),
            y=float(point[1]),
            z=float(point[2]),
            radius=float(radius),
        )

    def direction_of(self, vector: np.ndarray) -> np.ndarray:
        """The unit direction a raw vector points to on the board."""
        return self._direction(vector)

    def _direction(self, vector: np.ndarray) -> np.ndarray:
        projected = (vector - self.mean_vector) @ self._basis
        length = np.linalg.norm(projected)
        if length == 0:
            return _FALLBACK_DIRECTION
        return projected / length
