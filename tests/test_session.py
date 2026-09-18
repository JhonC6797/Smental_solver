import asyncio

import numpy as np
import pytest

from semantle.client import GuessResult
from server.projection import BoardProjection
from server.session import SolveSession
from solver.engine import SemantleEngine
from solver.vocabulary import Vocabulary


@pytest.fixture
def vocabulary():
    words = ["בית", "אוכל", "אדם", "מחשב", "כלב", "חתול"]
    rng = np.random.default_rng(5)
    vectors = rng.normal(size=(len(words), 8)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    return Vocabulary(words=words, vectors=vectors)


class InstantClient:
    """Scores without sleeping, so tests stay fast."""

    def __init__(self, winner):
        self.winner = winner

    def get_similarity(self, word):
        return GuessResult(word, 100.0 if word == self.winner else 20.0, None)


def _session(vocabulary, winner="בית"):
    projection = BoardProjection(vocabulary)
    return SolveSession(
        engine_factory=lambda: SemantleEngine(vocabulary, InstantClient(winner)),
        projection=projection,
    )


async def test_streams_messages_until_the_run_ends(vocabulary):
    session = _session(vocabulary)
    session.start()
    types = [message["type"] async for message in session.stream()]
    assert types[0] == "run_started"
    assert types[-1] == "solved"


async def test_history_records_everything_that_was_streamed(vocabulary):
    session = _session(vocabulary)
    session.start()
    streamed = [message async for message in session.stream()]
    assert session.history == streamed


async def test_a_late_subscriber_receives_the_backlog_first(vocabulary):
    """A browser that reloads mid-run must not lose the guesses already made."""
    session = _session(vocabulary)
    session.start()
    [message async for message in session.stream()]  # drain to completion
    replayed = [message async for message in session.stream()]
    assert replayed == session.history


async def test_the_session_reports_when_it_is_finished(vocabulary):
    session = _session(vocabulary)
    session.start()
    [message async for message in session.stream()]
    assert session.finished is True


def test_each_session_gets_its_own_id(vocabulary):
    assert _session(vocabulary).session_id != _session(vocabulary).session_id


async def test_two_readers_each_receive_the_whole_run(vocabulary):
    """A reload leaves the old connection briefly alive, so two streams can
    overlap. Neither may take a message the other needed."""
    session = _session(vocabulary)
    session.start()
    first, second = await asyncio.gather(
        _drain(session.stream()), _drain(session.stream())
    )
    assert first == second == session.history


async def _drain(stream):
    return [message async for message in stream]
