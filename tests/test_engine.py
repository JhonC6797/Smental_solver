import numpy as np
import pytest

from semantle.client import GuessResult
from solver import events
from solver.engine import SemantleEngine
from solver.vocabulary import Vocabulary


@pytest.fixture
def vocabulary():
    words = ["בית", "אוכל", "אדם", "מחשב", "כלב", "חתול", "שולחן", "מכונית"]
    rng = np.random.default_rng(0)
    vectors = rng.normal(size=(len(words), 8)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    return Vocabulary(words=words, vectors=vectors)


class ScriptedClient:
    """Returns a fixed score per word; unlisted words get `default`."""

    def __init__(self, scores, default=20.0):
        self.scores = scores
        self.default = default
        self.asked = []

    def get_similarity(self, word):
        self.asked.append(word)
        return GuessResult(word, self.scores.get(word, self.default), None)


class FailingClient:
    def __init__(self):
        self.asked = []

    def get_similarity(self, word):
        self.asked.append(word)
        return None


def run(engine):
    return list(engine.run())


def test_first_event_is_run_started(vocabulary):
    stream = run(SemantleEngine(vocabulary, ScriptedClient({})))
    assert isinstance(stream[0], events.RunStarted)
    assert stream[0].vocabulary_size == len(vocabulary)


def test_anchor_probes_are_emitted_as_guesses(vocabulary):
    """Anchors are real API calls and must appear on the board."""
    stream = run(SemantleEngine(vocabulary, ScriptedClient({})))
    guessed = [e.word for e in stream if isinstance(e, events.Guess)]
    assert "בית" in guessed


def test_guess_numbers_increase_by_one(vocabulary):
    stream = run(SemantleEngine(vocabulary, ScriptedClient({}), max_attempts=3))
    numbers = [e.guess_number for e in stream if isinstance(e, events.Guess)]
    assert numbers == list(range(1, len(numbers) + 1))


def test_reaching_one_hundred_emits_solved(vocabulary):
    client = ScriptedClient({"חתול": 100.0}, default=10.0)
    stream = run(SemantleEngine(vocabulary, client))
    solved = [e for e in stream if isinstance(e, events.Solved)]
    assert len(solved) == 1
    assert solved[0].word == "חתול"


def test_no_guesses_are_made_after_solving(vocabulary):
    client = ScriptedClient({"בית": 100.0})
    stream = run(SemantleEngine(vocabulary, client))
    assert isinstance(stream[-1], events.Solved)
    assert len(client.asked) == 1


def test_words_are_never_guessed_twice(vocabulary):
    client = ScriptedClient({})
    run(SemantleEngine(vocabulary, client, max_attempts=6))
    assert len(client.asked) == len(set(client.asked))


def test_a_persistently_failing_api_stops_the_run(vocabulary):
    """The original looped over the whole vocabulary without advancing."""
    client = FailingClient()
    stream = run(SemantleEngine(vocabulary, client, max_attempts=60))
    assert isinstance(stream[-1], events.Failed)
    assert len(client.asked) < 20


def test_an_unscored_word_does_not_poison_the_duplicate_filter(vocabulary):
    engine = SemantleEngine(vocabulary, FailingClient())
    run(engine)
    assert engine.tested_words == set()


def test_diagnostics_precede_the_guess_they_describe(vocabulary):
    stream = run(SemantleEngine(vocabulary, ScriptedClient({}), max_attempts=2))
    diagnostics = [e for e in stream if isinstance(e, events.Diagnostics)]
    assert diagnostics
    for diagnostic in diagnostics:
        following = [
            e for e in stream[stream.index(diagnostic):]
            if isinstance(e, events.Guess)
        ]
        assert following[0].guess_number == diagnostic.guess_number


def test_diagnostics_carry_the_target_estimate_as_a_direction(vocabulary):
    stream = run(SemantleEngine(vocabulary, ScriptedClient({}), max_attempts=2))
    diagnostic = next(e for e in stream if isinstance(e, events.Diagnostics))
    target = diagnostic.directions["target_estimate"]
    assert target.shape == (vocabulary.vectors.shape[1],)


def test_running_out_of_attempts_emits_failed(vocabulary):
    stream = run(SemantleEngine(vocabulary, ScriptedClient({}), max_attempts=1))
    assert isinstance(stream[-1], events.Failed)
