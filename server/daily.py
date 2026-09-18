"""One solve per day, shared by everyone who watches.

Every guess the solver makes is a real request to a game somebody else
runs. A board on the open web that solved the puzzle again for each visitor
would put twenty of those requests per visitor on that server, earn itself
a rate limit, and break in front of the next person. So the first visitor
of the day runs the search and everyone after them watches the recording.

Whether a recording is still current is settled by asking the game rather
than by watching a clock: one request asking whether the recorded answer
still scores 100. That is exact, it costs a single call instead of twenty,
and it does not depend on knowing what hour the puzzle turns over.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path

from server.session import SolveSession

RECORDING_FILENAME = "latest.json"
DEFAULT_REVALIDATE_SECONDS = 600


class RunStore:
    """Keeps the last completed run on disk so a restart need not re-solve."""

    def __init__(self, directory: Path) -> None:
        self._path = Path(directory) / RECORDING_FILENAME

    def load(self) -> tuple[str, list[dict]] | None:
        """The stored answer and its run, or None if there is nothing usable."""
        try:
            stored = json.loads(self._path.read_text(encoding="utf-8"))
            return stored["answer"], stored["history"]
        except (OSError, ValueError, KeyError, TypeError):
            # A missing, truncated or hand-edited file just means no recording.
            return None

    def save(self, answer: str, history: list[dict]) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps({"answer": answer, "history": history}, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            # An ephemeral or read-only disk costs one extra solve after a
            # restart. It must not take the board down.
            pass


def answer_of(history: list[dict]) -> str | None:
    for message in history:
        if message.get("type") == "solved":
            return message.get("word")
    return None


class DailyRuns:
    def __init__(
        self,
        start_session: Callable[[], SolveSession],
        still_correct: Callable[[str], bool],
        store: RunStore,
        revalidate_after: float = DEFAULT_REVALIDATE_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._start_session = start_session
        self._still_correct = still_correct
        self._store = store
        self._revalidate_after = revalidate_after
        self._clock = clock

        self._current: SolveSession | None = None
        self._answer: str | None = None
        self._saved = False
        self._checked_at: float | None = None

    def current(self) -> tuple[SolveSession, bool]:
        """The run to watch, and whether it is a recording rather than live."""
        if self._current is None:
            self._revive()
        if self._current is None:
            return self._begin(), False

        session = self._current
        if not session.finished:
            return session, False

        if not self._saved and not self._remember(session):
            return self._begin(), False  # the run failed; it is not worth keeping

        if self._due_for_check() and not self._still_correct(self._answer or ""):
            return self._begin(), False

        return session, True

    def invalidate_check(self) -> None:
        """Force the next visit to re-ask the game whether the answer holds."""
        self._checked_at = None

    def _revive(self) -> None:
        stored = self._store.load()
        if stored is None:
            return
        answer, history = stored
        self._answer = answer
        self._current = SolveSession.from_recording(history)
        self._saved = True
        self._checked_at = None  # a revived run is verified before it is served

    def _remember(self, session: SolveSession) -> bool:
        answer = answer_of(session.history)
        if answer is None:
            self._current = None
            return False
        self._answer = answer
        self._store.save(answer, session.history)
        self._saved = True
        self._checked_at = self._clock()  # just solved, so plainly current
        return True

    def _due_for_check(self) -> bool:
        return (
            self._checked_at is None
            or self._clock() - self._checked_at >= self._revalidate_after
        )

    def _begin(self) -> SolveSession:
        session = self._start_session()
        self._current = session
        self._answer = None
        self._saved = False
        self._checked_at = None
        session.on_finish = lambda: self._remember(session)
        session.start()
        return session
