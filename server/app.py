"""The web server.

It owns no algorithm knowledge: it hands out the day's run, forwards
whatever the engine emits, and adds board positions on the way out.

The day's puzzle is solved once and then replayed, so the number of
requests this board makes to the Semantle API does not grow with the
number of people watching it. See server/daily.py.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from semantle.client import SemantleClient
from server.daily import DailyRuns, RunStore
from server.projection import BASIS_FILENAME, BoardProjection
from server.session import SolveSession
from solver import config
from solver.engine import SemantleEngine
from solver.vocabulary import load_vocabulary

SOLVED_SIMILARITY = 100.0
DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"

app = FastAPI(title="Semantle Solver Board")

# Set ALLOWED_ORIGINS to the deployed site's URL; the default is the Vite
# dev server, which is where this runs during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(",")
        if origin.strip()
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

_runs: DailyRuns | None = None
_sessions: dict[str, SolveSession] = {}


def reset_state() -> None:
    """Drop cached state. Used by tests that swap the vocabulary."""
    global _runs
    _runs = None
    _sessions.clear()


def _daily() -> DailyRuns:
    """Build the day's run keeper once per process.

    The vocabulary and the projection basis are loaded here and shared:
    fitting the basis per request would be wasteful, and refitting it would
    move points that are already on a viewer's board.
    """
    global _runs
    if _runs is not None:
        return _runs

    vocabulary = load_vocabulary()
    projection = BoardProjection(vocabulary, config.VOCAB_DIR / BASIS_FILENAME)

    def still_correct(word: str) -> bool:
        result = SemantleClient().get_similarity(word)
        return result is not None and result.similarity >= SOLVED_SIMILARITY

    _runs = DailyRuns(
        start_session=lambda: SolveSession(
            engine_factory=lambda: SemantleEngine(vocabulary, SemantleClient()),
            projection=projection,
        ),
        still_correct=still_correct,
        store=RunStore(config.PROJECT_ROOT / "data" / "runs"),
    )
    return _runs


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True}


@app.post("/api/solve/start")
async def start_solve() -> dict:
    """Hand back the day's run: today's search, live or recorded."""
    session, recorded = _daily().current()
    _sessions[session.session_id] = session
    return {"session_id": session.session_id, "recorded": recorded}


@app.websocket("/ws/solve/{session_id}")
async def stream_solve(websocket: WebSocket, session_id: str) -> None:
    session = _sessions.get(session_id)
    if session is None:
        await websocket.close(code=4004)
        return

    await websocket.accept()
    try:
        async for message in session.stream():
            await websocket.send_json(message)
    except WebSocketDisconnect:
        pass
