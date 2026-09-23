import json

import numpy as np
import pytest

from semantle.client import GuessResult
from server.projection import BoardProjection
from scripts.publish_daily import (
    answer_of,
    build_recording,
    is_current,
    read_recording,
)
from solver.vocabulary import Vocabulary


@pytest.fixture
def vocabulary():
    words = ["בית", "אוכל", "אדם", "מחשב", "כלב", "חתול"]
    rng = np.random.default_rng(13)
    vectors = rng.normal(size=(len(words), 8)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    return Vocabulary(words=words, vectors=vectors)


class FakeClient:
    def __init__(self, winner="חתול"):
        self.winner = winner
        self.asked = []

    def get_similarity(self, word):
        self.asked.append(word)
        return GuessResult(word, 100.0 if word == self.winner else 20.0, None)


class UnreachableClient:
    def get_similarity(self, _word):
        return None


def test_a_recording_of_todays_word_costs_one_question():
    """The scheduled job runs several times a day; on the days nothing has
    changed it must not solve the puzzle again."""
    client = FakeClient()
    assert is_current({"answer": "חתול"}, client) is True
    assert client.asked == ["חתול"]


def test_a_recording_of_yesterdays_word_is_not_current():
    assert is_current({"answer": "בית"}, FakeClient()) is False


def test_a_missing_or_unusable_recording_is_not_current():
    assert is_current(None, FakeClient()) is False
    assert is_current({}, FakeClient()) is False


def test_an_unreachable_game_is_treated_as_not_current():
    assert is_current({"answer": "חתול"}, UnreachableClient()) is False


def test_a_recording_carries_the_answer_and_placed_guesses(vocabulary):
    recording = build_recording(vocabulary, BoardProjection(vocabulary), FakeClient())
    assert recording["answer"] == "חתול"
    assert recording["recorded_at"]
    guesses = [e for e in recording["events"] if e["type"] == "guess"]
    assert guesses
    assert set(guesses[0]["position"]) == {"x", "y", "z", "radius"}


def test_a_recording_is_json_safe(vocabulary):
    recording = build_recording(vocabulary, BoardProjection(vocabulary), FakeClient())
    json.dumps(recording)  # must not raise


def test_a_run_that_never_finds_the_word_is_not_published(vocabulary):
    """Overwriting a good recording with a failed run would leave the site
    showing nothing at all. This is an expected outcome the scheduled job
    retries later, not an error that should fail the workflow."""
    recording = build_recording(
        vocabulary, BoardProjection(vocabulary), FakeClient(winner="לא-קיימת")
    )
    assert recording is None


def test_a_failed_run_is_written_for_diagnosis_when_a_path_is_given(
    vocabulary, tmp_path
):
    """The board is how the suspect calibration constants get measured, so a
    failed run must not just vanish — it needs to be loadable for a look."""
    failed_path = tmp_path / "daily-failed.json"
    recording = build_recording(
        vocabulary,
        BoardProjection(vocabulary),
        FakeClient(winner="לא-קיימת"),
        failed_path,
    )
    assert recording is None

    dumped = json.loads(failed_path.read_text(encoding="utf-8"))
    assert dumped["answer"] is None
    assert dumped["recorded_at"]
    guesses = [e for e in dumped["events"] if e["type"] == "guess"]
    assert guesses


def test_answer_of_finds_nothing_in_a_run_that_failed():
    assert answer_of([{"type": "guess"}, {"type": "failed"}]) is None


def test_reading_a_corrupt_recording_returns_nothing(tmp_path):
    path = tmp_path / "daily.json"
    path.write_text("{ truncated", encoding="utf-8")
    assert read_recording(path) is None


def test_reading_a_missing_recording_returns_nothing(tmp_path):
    assert read_recording(tmp_path / "absent.json") is None
