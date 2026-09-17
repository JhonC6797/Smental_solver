"""The word list and its embedding matrix.

The raw FastText file is a multi-gigabyte text file. It is converted once
by scripts/build_vocab.py into a compact pair of files that load instantly;
nothing at runtime ever parses the .vec file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from solver import config
from solver.morphology import is_clean_hebrew


@dataclass(frozen=True)
class Vocabulary:
    """Words and their L2-normalised vectors, ordered by descending frequency."""

    words: list[str]
    vectors: np.ndarray
    word_to_index: dict[str, int] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "word_to_index", {word: i for i, word in enumerate(self.words)}
        )

    def __len__(self) -> int:
        return len(self.words)


def _normalise(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (vectors / norms).astype(np.float32)


def build_vocabulary(vec_path: Path, out_dir: Path, limit: int) -> Vocabulary:
    """Parse a FastText .vec file and write the compact artifact."""
    words: list[str] = []
    rows: list[np.ndarray] = []

    with open(vec_path, encoding="utf-8") as handle:
        handle.readline()  # header: "<word count> <dimensions>"
        for line in handle:
            if len(words) >= limit:
                break
            parts = line.rstrip().split(" ")
            word = parts[0]
            if not is_clean_hebrew(word):
                continue
            try:
                rows.append(np.array(parts[1:], dtype=np.float32))
            except ValueError:
                continue
            words.append(word)

    vectors = _normalise(np.vstack(rows))
    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / config.VECTORS_FILENAME, vectors)
    (out_dir / config.WORDS_FILENAME).write_text(
        json.dumps(words, ensure_ascii=False), encoding="utf-8"
    )
    return Vocabulary(words=words, vectors=vectors)


def load_vocabulary(directory: Path | None = None) -> Vocabulary:
    """Load the artifact built by scripts/build_vocab.py."""
    directory = directory or config.VOCAB_DIR
    vectors_path = directory / config.VECTORS_FILENAME
    words_path = directory / config.WORDS_FILENAME
    if not vectors_path.exists() or not words_path.exists():
        raise FileNotFoundError(
            f"No vocabulary artifact in {directory}. "
            "Build it with: python -m scripts.build_vocab"
        )
    words = json.loads(words_path.read_text(encoding="utf-8"))
    return Vocabulary(words=words, vectors=np.load(vectors_path))
