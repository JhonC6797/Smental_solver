"""One solve run, streamed to whoever is watching.

The engine blocks on network calls, so it runs in a worker thread and the
events cross into the event loop through a queue. Everything streamed is
also kept in `history`, so a browser that reloads mid-run replays what it
missed and then joins the live stream.
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from collections.abc import AsyncIterator, Callable

from server.projection import BoardProjection
from server.serialization import serialize
from solver.engine import SemantleEngine

_DONE = object()


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
        self._queue: asyncio.Queue = asyncio.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

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
            self._publish(_DONE)

    def _publish(self, message) -> None:
        self._loop.call_soon_threadsafe(self._queue.put_nowait, message)

    async def stream(self) -> AsyncIterator[dict]:
        """Replay what has happened, then follow the run live."""
        replayed = 0
        while replayed < len(self.history):
            yield self.history[replayed]
            replayed += 1

        if self.finished:
            return

        while True:
            message = await self._queue.get()
            if message is _DONE:
                self.finished = True
                return
            self.history.append(message)
            yield message
