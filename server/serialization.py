"""Turn engine events into JSON-safe messages for the browser.

This is where a guess acquires its position on the board: the engine emits
a word and a score, and the projection turns those into coordinates. It is
also the boundary that keeps 300-dimension vectors off the wire — a
diagnostics direction is projected to a 3D unit vector before it is sent.
"""

from __future__ import annotations

from typing import Any

from server.projection import BoardProjection
from solver import events


def _position(projection: BoardProjection, word: str, similarity: float) -> dict:
    placed = projection.place(word, similarity)
    return {
        "x": placed.x,
        "y": placed.y,
        "z": placed.z,
        "radius": placed.radius,
    }


def serialize(event: events.Event, projection: BoardProjection) -> dict[str, Any]:
    if isinstance(event, events.RunStarted):
        return {
            "type": "run_started",
            "vocabulary_size": event.vocabulary_size,
            "started_at": event.started_at.isoformat(),
        }

    if isinstance(event, events.Guess):
        return {
            "type": "guess",
            "word": event.word,
            "similarity": event.similarity,
            "rank": event.rank,
            "guess_number": event.guess_number,
            "is_best_so_far": event.is_best_so_far,
            "best_word": event.best_word,
            "best_similarity": event.best_similarity,
            "position": _position(projection, event.word, event.similarity),
        }

    if isinstance(event, events.Solved):
        return {
            "type": "solved",
            "word": event.word,
            "total_guesses": event.total_guesses,
            "elapsed_seconds": event.elapsed_seconds,
        }

    if isinstance(event, events.Failed):
        return {"type": "failed", "reason": event.reason}

    if isinstance(event, events.Diagnostics):
        return {
            "type": "diagnostics",
            "guess_number": event.guess_number,
            "scalars": {k: float(v) for k, v in event.scalars.items()},
            "directions": {
                name: [float(v) for v in projection.direction_of(vector)]
                for name, vector in event.directions.items()
            },
            "word_scores": {
                name: [[word, float(score)] for word, score in pairs]
                for name, pairs in event.word_scores.items()
            },
        }

    raise TypeError(f"unknown event type: {type(event).__name__}")
