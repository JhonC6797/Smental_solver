"""The web server.

It owns no algorithm knowledge: it starts a run, forwards whatever the
engine emits, and adds board positions on the way out.
"""

from __future__ import annotations

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from semantle.client import SemantleClient
from server.projection import BoardProjection
from server.session import SolveSession
from solver.engine import SemantleEngine
from solver.vocabulary import load_vocabulary

app = FastAPI(title="Semantle Solver Board")

# The Vite dev server runs on a different port during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_sessions: dict[str, SolveSession] = {}
_vocabulary = None
_projection: BoardProjection | None = None


def reset_state() -> None:
    """Drop cached state. Used by tests that swap the vocabulary."""
    global _vocabulary, _projection
    _vocabulary = None
    _projection = None
    _sessions.clear()


def _ensure_loaded() -> tuple:
    """Load the vocabulary and fit the projection basis once per process.

    Refitting the basis per request would move points that are already on
    the board, so it is built once and shared.
    """
    global _vocabulary, _projection
    if _vocabulary is None:
        _vocabulary = load_vocabulary()
        _projection = BoardProjection(_vocabulary)
    return _vocabulary, _projection


@app.post("/api/solve/start")
async def start_solve() -> dict:
    vocabulary, projection = _ensure_loaded()
    session = SolveSession(
        engine_factory=lambda: SemantleEngine(vocabulary, SemantleClient()),
        projection=projection,
    )
    _sessions[session.session_id] = session
    session.start()
    return {"session_id": session.session_id}


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
