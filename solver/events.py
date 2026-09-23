"""What the engine emits.

Core events (RunStarted, Guess, Solved, Failed) are true of ANY search
algorithm; consumers may rely on them. Diagnostics is deliberately generic:
its three dictionaries hold whatever the current algorithm computes, keyed
by name, so replacing the algorithm changes the contents and never the
contract. Consumers render Diagnostics by VALUE TYPE, never by key name.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np


@dataclass(frozen=True)
class RunStarted:
    vocabulary_size: int
    started_at: datetime


@dataclass(frozen=True)
class Guess:
    word: str
    similarity: float
    rank: int | None
    guess_number: int
    is_best_so_far: bool
    best_word: str
    best_similarity: float


@dataclass(frozen=True)
class Solved:
    word: str
    total_guesses: int
    elapsed_seconds: float


@dataclass(frozen=True)
class Failed:
    """Giving up is true of any search algorithm, and so is having a best
    candidate on hand when it happens — a consumer may publish that
    candidate rather than showing nothing."""

    reason: str
    best_word: str | None = None
    best_similarity: float = -1.0


@dataclass(frozen=True)
class Diagnostics:
    """Algorithm internals for the guess that is about to be made."""

    guess_number: int
    scalars: dict[str, float] = field(default_factory=dict)
    directions: dict[str, np.ndarray] = field(default_factory=dict)
    word_scores: dict[str, list[tuple[str, float]]] = field(default_factory=dict)


Event = RunStarted | Guess | Solved | Failed | Diagnostics
