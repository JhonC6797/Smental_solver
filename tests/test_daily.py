import json

import numpy as np
import pytest

from semantle.client import GuessResult
from server.daily import DailyRuns, RunStore
from server.projection import BoardProjection
from server.session import SolveSession
from solver.engine import SemantleEngine
from solver.vocabulary import Vocabulary


@pytest.fixture
def vocabulary():
    words = ["בית", "אוכל", "אדם", "מחשב", "כלב", "חתול"]
    rng = np.random.default_rng(11)
    vectors = rng.normal(size=(len(words), 8)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    return Vocabulary(words=words, vectors=vectors)


class CountingClient:
    """Scores without sleeping, and counts what the game was asked."""

    # Not one of the configured anchors, so the engine has to search for it.
    def __init__(self, winner="חתול"):
        self.winner = winner
        self.calls = 0

    def get_similarity(self, word):
        self.calls += 1
        return GuessResult(word, 100.0 if word == self.winner else 20.0, None)


def make_runs(vocabulary, client, store, still_correct=None):
    projection = BoardProjection(vocabulary)
    return DailyRuns(
        start_session=lambda: SolveSession(
            engine_factory=lambda: SemantleEngine(vocabulary, client),
            projection=projection,
        ),
        still_correct=still_correct or (lambda word: word == client.winner),
        store=store,
    )


async def drain(session):
    return [message async for message in session.stream()]


async def test_the_first_visitor_runs_a_real_search(vocabulary, tmp_path):
    client = CountingClient()
    runs = make_runs(vocabulary, client, RunStore(tmp_path))
    session, recorded = runs.current()
    await drain(session)
    assert recorded is False
    assert client.calls > 1  # anchors were probed and a search followed


async def test_later_visitors_get_the_recording_without_asking_the_game(
    vocabulary, tmp_path
):
    """A public board must not fire a fresh burst of guesses per visitor."""
    client = CountingClient()
    runs = make_runs(vocabulary, client, RunStore(tmp_path))
    first, _ = runs.current()
    await drain(first)
    spent = client.calls

    second, recorded = runs.current()
    history = await drain(second)
    assert recorded is True
    assert client.calls == spent  # not one extra call
    assert history == first.history


async def test_the_recording_is_dropped_once_the_word_changes(vocabulary, tmp_path):
    client = CountingClient()
    valid = {"ok": True}
    runs = make_runs(
        vocabulary, client, RunStore(tmp_path), still_correct=lambda _word: valid["ok"]
    )
    first, _ = runs.current()
    await drain(first)

    valid["ok"] = False
    runs.invalidate_check()
    session, recorded = runs.current()
    await drain(session)
    assert recorded is False


async def test_validity_is_not_rechecked_on_every_visit(vocabulary, tmp_path):
    checks = {"count": 0}

    def still_correct(_word):
        checks["count"] += 1
        return True

    client = CountingClient()
    runs = make_runs(vocabulary, client, RunStore(tmp_path), still_correct)
    first, _ = runs.current()
    await drain(first)
    for _ in range(5):
        runs.current()
    assert checks["count"] <= 1


async def test_a_run_still_in_progress_is_shared_rather_than_restarted(
    vocabulary, tmp_path
):
    client = CountingClient()
    runs = make_runs(vocabulary, client, RunStore(tmp_path))
    first, _ = runs.current()
    second, recorded = runs.current()
    assert second is first
    assert recorded is False
    await drain(first)


async def test_the_recording_survives_a_restart(vocabulary, tmp_path):
    client = CountingClient()
    store = RunStore(tmp_path)
    first, _ = make_runs(vocabulary, client, store).current()
    await drain(first)
    spent = client.calls

    revived = make_runs(vocabulary, client, store)
    session, recorded = revived.current()
    history = await drain(session)
    assert recorded is True
    assert client.calls == spent
    assert [m["type"] for m in history] == [m["type"] for m in first.history]


def test_the_store_ignores_a_corrupt_file(tmp_path):
    (tmp_path / "latest.json").write_text("{not json", encoding="utf-8")
    assert RunStore(tmp_path).load() is None


def test_the_store_round_trips_a_run(tmp_path):
    store = RunStore(tmp_path)
    store.save("עץ", [{"type": "solved", "word": "עץ"}])
    assert store.load() == ("עץ", [{"type": "solved", "word": "עץ"}])


def test_the_store_ignores_a_file_missing_its_answer(tmp_path):
    (tmp_path / "latest.json").write_text(json.dumps({"history": []}), encoding="utf-8")
    assert RunStore(tmp_path).load() is None
