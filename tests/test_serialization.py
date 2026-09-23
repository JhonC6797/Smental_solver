from datetime import datetime, timezone

import numpy as np
import pytest

from server.projection import BoardProjection
from server.serialization import serialize
from solver import events
from solver.vocabulary import Vocabulary


@pytest.fixture
def projection():
    words = ["בית", "אוכל", "כלב"]
    rng = np.random.default_rng(3)
    vectors = rng.normal(size=(len(words), 8)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    return BoardProjection(Vocabulary(words=words, vectors=vectors))


def test_a_guess_carries_its_board_position(projection):
    message = serialize(
        events.Guess("כלב", 42.0, 847, 3, True, "כלב", 42.0), projection
    )
    assert message["type"] == "guess"
    assert message["word"] == "כלב"
    assert message["similarity"] == 42.0
    assert message["rank"] == 847
    assert set(message["position"]) == {"x", "y", "z", "radius"}


def test_run_started_is_json_safe(projection):
    message = serialize(events.RunStarted(22000, datetime.now(timezone.utc)), projection)
    assert message["type"] == "run_started"
    assert isinstance(message["started_at"], str)


def test_solved_and_failed_are_tagged(projection):
    assert serialize(events.Solved("עץ", 19, 12.8), projection)["type"] == "solved"
    assert serialize(events.Failed("gave up"), projection)["type"] == "failed"


def test_a_failed_run_carries_its_best_candidate(projection):
    """The board can offer the best guess it found instead of showing
    nothing, so giving up must not drop that information."""
    message = serialize(
        events.Failed("ran out of attempts", best_word="כלב", best_similarity=74.2),
        projection,
    )
    assert message["best_word"] == "כלב"
    assert message["best_similarity"] == 74.2


def test_diagnostics_directions_are_projected_to_three_numbers(projection):
    event = events.Diagnostics(
        guess_number=4,
        scalars={"temperature": 8.0},
        directions={"target_estimate": np.ones(8, dtype=np.float32)},
        word_scores={"top_candidates": [("כלב", 0.5)]},
    )
    message = serialize(event, projection)
    assert message["type"] == "diagnostics"
    assert len(message["directions"]["target_estimate"]) == 3
    assert message["scalars"]["temperature"] == 8.0
    assert message["word_scores"]["top_candidates"][0] == ["כלב", 0.5]


def test_every_message_survives_json_encoding(projection):
    import json

    event = events.Diagnostics(
        guess_number=1,
        scalars={"mode": 0.0},
        directions={"target_estimate": np.ones(8, dtype=np.float32)},
    )
    json.dumps(serialize(event, projection))  # must not raise
