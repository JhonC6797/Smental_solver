"""One solve run, streamed to whoever is watching.

The engine blocks on network calls, so it runs in a worker thread and its
events cross into the event loop one at a time. Every event is appended to
`history` and readers follow that list by index rather than consuming a
queue, so any number of readers can watch the same run and none of them can
take a message another one needed. That is what makes reconnecting work: a
browser that reloads mid-run replays what it missed and then joins the live
stream, even if its previous connection has not been torn down yet.
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from collections.abc import AsyncIterator, Callable

from server.projection import BoardProjection
from server.serialization import serialize
from solver.engine import SemantleEngine


class SolveSession:
    def __init__(
        self,
        engine_factory: Callable[[], SemantleEngine],
        projection: BoardProjection,
    ) -> None:
        self.session_id = uuid.uuid4().hex
        self.history: list[dict] = []
        self.finished = False
        self._engine_factory = engine_factory
        self._projection = projection
        self._arrived = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        # Called once, on the event loop, the moment the run ends. It is how
        # a completed run gets kept without waiting for the next visitor.
        self.on_finish: Callable[[], None] | None = None

    @classmethod
    def from_recording(cls, history: list[dict]) -> "SolveSession":
        """A finished run rebuilt from a stored history.

        It has no engine and never starts a thread: readers replay it and
        the stream ends, exactly as it would for a live run that is over.
        """
        session = cls.__new__(cls)
        session.session_id = uuid.uuid4().hex
        session.history = list(history)
        session.finished = True
        session._engine_factory = None
        session._projection = None
        session._arrived = asyncio.Event()
        session._loop = None
        session._thread = None
        session.on_finish = None
        return session

    def start(self) -> None:
        self._loop = asyncio.get_event_loop()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        """Runs on the worker thread; never touches the loop directly."""
        try:
            for event in self._engine_factory().run():
                self._publish(serialize(event, self._projection))
        except Exception as error:  # surfaced to the browser, not swallowed
            self._publish({"type": "failed", "reason": str(error)})
        finally:
            self._publish(None)

    def _publish(self, message: dict | None) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._record, message)

    def _record(self, message: dict | None) -> None:
        """Runs on the event loop, so history and the flag stay consistent."""
        if message is None:
            self.finished = True
            if self.on_finish is not None:
                self.on_finish()
        else:
            self.history.append(message)
        self._arrived.set()

    async def stream(self) -> AsyncIterator[dict]:
        """Replay what has happened, then follow the run live."""
        index = 0
        while True:
            while index < len(self.history):
                yield self.history[index]
                index += 1
            if self.finished:
                return
            # Clear first, then re-check, so an event that lands in between
            # is seen by the loop above instead of being waited past.
            self._arrived.clear()
            if index < len(self.history) or self.finished:
                continue
            await self._arrived.wait()
