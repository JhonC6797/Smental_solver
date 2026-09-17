"""The search algorithm.

Two phases. First it probes a fixed list of anchor words to find a region of
meaning that scores well. Then it repeatedly estimates where the answer is —
as a softmax-weighted blend of the anchors it has scored, pushed away from
regions that scored badly — and guesses the nearest unused word to that
estimate. Above FOCUS_THRESHOLD it switches to plain nearest-neighbour
search around the best word found so far.

The engine yields events and never prints. It knows nothing about the server
or the board.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import datetime, timezone

import numpy as np

from solver import config, events
from solver.morphology import is_too_similar_fast
from solver.vocabulary import Vocabulary

_GRAVITY_MODE = 0.0
_NEAREST_NEIGHBOUR_MODE = 1.0
_SOLVED_SIMILARITY = 100.0


class SemantleEngine:
    def __init__(
        self,
        vocabulary: Vocabulary,
        client,
        max_attempts: int = config.MAX_ATTEMPTS,
    ) -> None:
        self.vocabulary = vocabulary
        self.client = client
        self.max_attempts = max_attempts

        self.checked_indices: set[int] = set()
        self.tested_words: set[str] = set()
        self.scored_indices: list[int] = []
        self.scored_similarities: list[float] = []
        self.bad_indices: list[int] = []

        self.best_word: str | None = None
        self.best_similarity = -1.0
        self.stagnant_count = 0
        self.guess_number = 0

        # Words arrive in descending frequency order, so a gentle linear
        # penalty nudges the search towards commoner words.
        self.frequency_bias = np.linspace(
            0.0, config.FREQUENCY_BIAS_SPAN, len(vocabulary), dtype=np.float32
        )

    def run(self) -> Iterator[events.Event]:
        started = time.monotonic()
        yield events.RunStarted(
            vocabulary_size=len(self.vocabulary),
            started_at=datetime.now(timezone.utc),
        )

        for event in self._probe_anchors():
            yield event
            if self._is_solved():
                yield self._solved(started)
                return

        if not self.scored_similarities:
            yield events.Failed(reason="no anchor word returned a usable score")
            return

        for event in self._search():
            yield event
            if isinstance(event, events.Failed):
                return
            if self._is_solved():
                yield self._solved(started)
                return

        yield events.Failed(reason="ran out of attempts before reaching 100%")

    def _is_solved(self) -> bool:
        return self.best_similarity >= _SOLVED_SIMILARITY

    def _solved(self, started: float) -> events.Solved:
        return events.Solved(
            word=self.best_word,
            total_guesses=self.guess_number,
            elapsed_seconds=time.monotonic() - started,
        )

    def _probe_anchors(self) -> Iterator[events.Event]:
        for anchor in config.INITIAL_ANCHORS:
            index = self.vocabulary.word_to_index.get(anchor)
            if index is None:
                continue
            guess = self._submit(index, mark_bad=False)
            if guess is not None:
                yield guess

    def _search(self) -> Iterator[events.Event]:
        attempt = 0
        consecutive_failures = 0

        while attempt < self.max_attempts:
            attempt += 1  # always advances, even when the API call fails
            scores, target, scalars = self._score_candidates()
            index = self._pick_candidate(scores)
            if index is None:
                yield events.Failed(reason="no unused candidate words remain")
                return

            yield self._diagnostics(scores, target, scalars)

            guess = self._submit(index, mark_bad=True)
            if guess is None:
                consecutive_failures += 1
                if consecutive_failures >= config.MAX_CONSECUTIVE_FAILURES:
                    yield events.Failed(reason="the Semantle API kept failing")
                    return
                continue

            consecutive_failures = 0
            yield guess

    def _score_candidates(self) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
        vectors = self.vocabulary.vectors
        scalars = {"stagnant_count": float(self.stagnant_count)}

        if self.best_similarity >= config.FOCUS_THRESHOLD:
            scalars["mode"] = _NEAREST_NEIGHBOUR_MODE
            best_index = self.scored_indices[int(np.argmax(self.scored_similarities))]
            target = vectors[best_index]
            scores = vectors @ target
        else:
            scalars["mode"] = _GRAVITY_MODE
            target, weights = self._estimate_target()
            scalars["temperature"] = self._temperature()
            scalars["effective_anchor_count"] = float(1.0 / np.sum(weights**2))
            scores = vectors @ target
            if self.bad_indices:
                repulsion = np.max(vectors @ vectors[self.bad_indices].T, axis=1)
                penalty = config.REPULSION_BASE + (
                    self.stagnant_count * config.REPULSION_STEP
                )
                scalars["penalty_weight"] = float(penalty)
                scores = scores - penalty * np.maximum(
                    0.0, repulsion - config.REPULSION_FLOOR
                )

        scores = scores + self.frequency_bias
        if self.checked_indices:
            scores[list(self.checked_indices)] = -np.inf
        return scores, target, scalars

    def _temperature(self) -> float:
        if self.best_similarity >= config.HIGH_SCORE_THRESHOLD:
            return config.TEMPERATURE_FOCUSED
        return config.TEMPERATURE_BROAD

    def _estimate_target(self) -> tuple[np.ndarray, np.ndarray]:
        observed = np.array(self.scored_similarities, dtype=np.float32)
        weights = np.exp(observed / self._temperature())
        weights = weights / np.sum(weights)
        target = weights @ self.vocabulary.vectors[self.scored_indices]
        norm = np.linalg.norm(target)
        if norm > 0:
            target = target / norm
        return target.astype(np.float32), weights

    def _pick_candidate(self, scores: np.ndarray) -> int | None:
        for index in np.argsort(scores)[::-1]:
            index = int(index)
            word = self.vocabulary.words[index]
            if word in self.tested_words:
                continue
            if is_too_similar_fast(word, self.tested_words):
                self.checked_indices.add(index)
                continue
            return index
        return None

    def _diagnostics(
        self, scores: np.ndarray, target: np.ndarray, scalars: dict[str, float]
    ) -> events.Diagnostics:
        finite = np.isfinite(scores)
        ranked = np.argsort(scores)[::-1][: config.TOP_CANDIDATES_REPORTED]
        top = [
            (self.vocabulary.words[int(i)], float(scores[int(i)]))
            for i in ranked
            if finite[int(i)]
        ]
        return events.Diagnostics(
            guess_number=self.guess_number + 1,
            scalars=scalars,
            directions={"target_estimate": np.asarray(target, dtype=np.float32)},
            word_scores={"top_candidates": top},
        )

    def _submit(self, index: int, mark_bad: bool) -> events.Guess | None:
        """Score one word and fold the result into the engine's state."""
        word = self.vocabulary.words[index]
        self.checked_indices.add(index)

        result = self.client.get_similarity(word)
        if result is None:
            # Deliberately NOT added to tested_words: a word that was never
            # scored must not block its whole family from being guessed.
            return None

        self.tested_words.add(word)
        self.guess_number += 1

        if result.similarity > 0:
            self.scored_indices.append(index)
            self.scored_similarities.append(result.similarity)

        is_best = result.similarity > self.best_similarity
        if is_best:
            self.best_word = word
            self.best_similarity = result.similarity
            self.stagnant_count = 0
        else:
            self.stagnant_count += 1
            if mark_bad and result.similarity < config.BAD_WORD_THRESHOLD:
                self.bad_indices.append(index)

        return events.Guess(
            word=word,
            similarity=result.similarity,
            rank=result.rank,
            guess_number=self.guess_number,
            is_best_so_far=is_best,
            best_word=self.best_word,
            best_similarity=self.best_similarity,
        )
